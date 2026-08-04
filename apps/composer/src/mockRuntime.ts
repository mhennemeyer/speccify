// Mock-Bundle-Laufzeit: kompiliert die vom Backend gelieferte Mock-Closure
// (`POST /api/v1/mock/draft`) im Browser und macht die Komponenten als echte
// React-Komponenten verfügbar.
//
// Warum: Der Canvas soll den **generierten Mock** rendern, nicht eine zweite
// Interpretation des API-Vertrags. Was hier läuft, sind byte-identisch die
// Dateien, die `speccify mock` auf die Platte schreibt — kein LLM, kein Netz
// über den einen Endpoint hinaus, keine Drift zwischen Vorschau und Output.
//
// Ablauf: sucrase transpiliert TSX → CommonJS (nur Syntax, kein Typecheck),
// ein Mini-`require` löst die relativen Importe innerhalb der Closure auf und
// bindet `"react"` an *unsere* React-Instanz (sonst brechen Hooks).

import * as React from "react";
import { transform } from "sucrase";

export interface MockModule {
  default?: unknown;
  [key: string]: unknown;
}

export class MockRuntimeError extends Error {}

export interface MockRuntime {
  /** Modul laden (Pfad wie in der Closure, z. B. `org/Button.mock.tsx`). */
  load(path: string): MockModule;
  /** Default-Export als React-Komponente; `null`, wenn keiner existiert (z. B. logic-Mocks). */
  component(path: string): React.ComponentType<Record<string, unknown>> | null;
  /** Rohe Quelldateien der Closure (für die YAML/Code-Ansicht). */
  files: Record<string, string>;
}

const EXTENSIONS = ["", ".tsx", ".ts"];

function dirname(path: string): string {
  const index = path.lastIndexOf("/");
  return index === -1 ? "" : path.slice(0, index);
}

function normalize(path: string): string {
  const parts: string[] = [];
  for (const segment of path.split("/")) {
    if (segment === "" || segment === ".") continue;
    if (segment === "..") {
      parts.pop();
      continue;
    }
    parts.push(segment);
  }
  return parts.join("/");
}

function resolve(importer: string, specifier: string, files: Record<string, string>): string {
  const base = normalize(`${dirname(importer)}/${specifier}`);
  for (const extension of EXTENSIONS) {
    if (`${base}${extension}` in files) return `${base}${extension}`;
  }
  throw new MockRuntimeError(
    `Mock-Modul '${specifier}' (aus '${importer}') ist nicht Teil der Closure.`,
  );
}

export function createMockRuntime(files: Record<string, string>): MockRuntime {
  const modules = new Map<string, MockModule>();
  const loading = new Set<string>();

  function load(path: string): MockModule {
    const cached = modules.get(path);
    if (cached) return cached;
    const source = files[path];
    if (source === undefined) {
      throw new MockRuntimeError(`Mock-Modul '${path}' fehlt in der Closure.`);
    }
    if (loading.has(path)) {
      throw new MockRuntimeError(`Zyklischer Mock-Import bei '${path}'.`);
    }
    loading.add(path);
    try {
      const { code } = transform(source, {
        transforms: ["typescript", "jsx", "imports"],
        jsxRuntime: "classic",
        filePath: path,
        production: true,
      });
      const module_: { exports: MockModule } = { exports: {} };
      const require = (specifier: string): unknown => {
        if (specifier === "react") return React;
        if (specifier.startsWith(".")) return load(resolve(path, specifier, files));
        throw new MockRuntimeError(
          `Mock-Modul '${path}' importiert '${specifier}' — im Composer sind nur ` +
            `relative Closure-Importe und "react" auflösbar.`,
        );
      };
      // eslint-disable-next-line @typescript-eslint/no-implied-eval
      const factory = new Function("require", "module", "exports", code) as (
        require_: (specifier: string) => unknown,
        module__: { exports: MockModule },
        exports: MockModule,
      ) => void;
      factory(require, module_, module_.exports);
      modules.set(path, module_.exports);
      return module_.exports;
    } catch (error) {
      if (error instanceof MockRuntimeError) throw error;
      throw new MockRuntimeError(`Mock-Modul '${path}' ist nicht ausführbar: ${String(error)}`);
    } finally {
      loading.delete(path);
    }
  }

  return {
    files,
    load,
    component(path) {
      const exported = load(path).default;
      return typeof exported === "function"
        ? (exported as React.ComponentType<Record<string, unknown>>)
        : null;
    },
  };
}

// --- Namensregeln, gespiegelt aus `core/codegen/mock_react.py` ----------------
//
// Der Composer muss Props/Events/Slots so benennen, wie der Generator sie in
// die TSX-Signatur schreibt (snake_case → camelCase, Event `pressed` →
// `onPressed`). Einzige verbleibende Kopplung an den Generator — die Regeln
// sind bewusst trivial gehalten.

// `str.capitalize()` aus Python: erster Buchstabe groß, Rest klein.
function capitalize(part: string): string {
  return part[0].toUpperCase() + part.slice(1).toLowerCase();
}

export function camel(snake: string): string {
  const parts = snake.split("_").filter(Boolean);
  if (parts.length === 0) return snake;
  return parts[0] + parts.slice(1).map(capitalize).join("");
}

export function eventPropName(eventName: string): string {
  return "on" + eventName.split("_").filter(Boolean).map(capitalize).join("");
}

export function componentName(specId: string): string {
  const name = specId.replace(/^@/, "").split("/")[1] ?? "";
  return name.replace(/_/g, "-").split("-").filter(Boolean).map(capitalize).join("");
}

/** Pfad einer Spec innerhalb der Mock-Closure (= `mock_output_path` im Core). */
export function mockModulePath(specId: string, kind: string): string {
  const scope = specId.replace(/^@/, "").split("/")[0] ?? "";
  const extension = kind === "logic" ? "ts" : "tsx";
  return `${scope}/${componentName(specId)}.mock.${extension}`;
}
