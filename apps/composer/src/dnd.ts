// Drag & Drop im Composer: eigene MIME-Typen, damit `dragover` schon an den
// `dataTransfer.types` erkennt, ob ein Drop hier überhaupt zulässig ist
// (`getData` ist im Protected Mode während `dragover` leer).
//
// Zwei Nutzlasten: eine Spec aus der Palette (neuer Knoten) und ein
// bestehender Knoten aus dem Canvas (Umhängen samt Teilbaum).

export const DRAG_SPEC = "application/x-speccify-spec";
export const DRAG_NODE = "application/x-speccify-node";

export function dragKind(transfer: DataTransfer): "spec" | "node" | null {
  const types = Array.from(transfer.types);
  if (types.includes(DRAG_SPEC)) return "spec";
  if (types.includes(DRAG_NODE)) return "node";
  return null;
}
