// Native Toolbox (T2): Manifeste kommen aus dem Rust-Kern
// (crates/toolbox — builtin + ~/.speccify/toolbox + Working Dir),
// nicht mehr über die dotagent-CLI.

import { invoke } from "@tauri-apps/api/core";

export interface ToolboxRun {
  command: string;
  args: string[];
  transport: "stdio" | "sse" | "http";
  autostart: boolean;
}

export interface ToolboxManifest {
  kind: "tool" | "mcp" | "kb";
  name: string;
  slug: string;
  description: string;
  tags: string[];
  category: string;
  run: ToolboxRun | null;
  requires_binaries: string[];
  source: "builtin" | "global" | "workingdir";
  path: string | null;
}

export interface ToolboxList {
  manifests: ToolboxManifest[];
  warnings: string[];
}

export const fetchToolbox = () => invoke<ToolboxList>("toolbox_list");

export const scaffoldManifest = (slug: string, kind: string, name: string) =>
  invoke<string>("toolbox_scaffold", { slug, kind, name });
