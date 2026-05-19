/**
 * Typed fetch wrappers for the Speccify backend.
 *
 * The browser hits `/api/v1/*` on the Next origin; `next.config.ts` rewrites
 * those calls to the FastAPI backend (default `http://localhost:8000`). That
 * keeps CORS noise out of the playground UI.
 *
 * All responses are validated with zod so a backend contract drift becomes a
 * runtime error in the UI instead of silently propagating `any`.
 */

import { z } from "zod";

export const SpecEntrySchema = z.object({
  id: z.string(),
  version: z.string(),
  title: z.string(),
  yaml: z.string(),
});
export type SpecEntry = z.infer<typeof SpecEntrySchema>;

const SpecListSchema = z.object({
  specs: z.array(SpecEntrySchema),
});

export const GeneratorPinSchema = z
  .object({
    kind: z.string(),
    model: z.string(),
    prompt_version: z.string(),
    cache_key: z.string(),
    seed: z.number().nullable().optional(),
  })
  .passthrough();
export type GeneratorPin = z.infer<typeof GeneratorPinSchema>;

export const RenderResultSchema = z.object({
  spec_id: z.string(),
  target: z.string(),
  files: z.record(z.string(), z.string()),
  generator_pin: GeneratorPinSchema.nullable(),
});
export type RenderResult = z.infer<typeof RenderResultSchema>;

/**
 * Structured backend error. The backend returns it as `detail` of an
 * HTTPException; we surface `error_code` to the UI so the `ErrorPanel` can
 * branch on `cache_miss` vs. `spec_invalid` vs. `unknown_target`.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string;
  readonly details?: unknown;
  readonly hint?: string;

  constructor(params: {
    status: number;
    errorCode: string;
    message: string;
    details?: unknown;
    hint?: string;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.errorCode = params.errorCode;
    this.details = params.details;
    this.hint = params.hint;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    // non-JSON body → fall through to generic shape
  }
  const detail =
    body && typeof body === "object" && "detail" in body
      ? (body as { detail: unknown }).detail
      : body;
  if (detail && typeof detail === "object") {
    const obj = detail as Record<string, unknown>;
    return new ApiError({
      status: res.status,
      errorCode: typeof obj.error_code === "string" ? obj.error_code : "unknown",
      message: typeof obj.message === "string" ? obj.message : res.statusText,
      details: obj.details,
      hint: typeof obj.hint === "string" ? obj.hint : undefined,
    });
  }
  return new ApiError({
    status: res.status,
    errorCode: "unknown",
    message: typeof detail === "string" ? detail : res.statusText,
  });
}

export async function listSpecs(): Promise<SpecEntry[]> {
  const res = await fetch("/api/v1/specs", { cache: "no-store" });
  if (!res.ok) throw await parseError(res);
  const json = await res.json();
  return SpecListSchema.parse(json).specs;
}

export interface RenderRequest {
  specId: string;
  version: string;
  specYaml: string;
  target: string;
}

export async function renderSpec(req: RenderRequest): Promise<RenderResult> {
  const res = await fetch("/api/v1/render", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      spec_id: req.specId,
      version: req.version,
      spec_yaml: req.specYaml,
      target: req.target,
    }),
  });
  if (!res.ok) throw await parseError(res);
  const json = await res.json();
  return RenderResultSchema.parse(json);
}
