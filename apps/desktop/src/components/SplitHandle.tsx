// Ziehgriff zwischen zwei Bereichen (W7-Layout). Pointer-Capture hält den
// Zeiger auch über dem xterm-Canvas oder Iframes am Griff; während des
// Ziehens sind Textauswahl und Cursor global gesetzt, damit nichts
// „mitmarkiert" wird. Doppelklick setzt auf den Default zurück.

import { useRef } from "react";
import type { PointerEvent } from "react";

export default function SplitHandle({
  axis,
  size,
  invert = false,
  onResize,
  onReset,
  className = "",
  style,
}: {
  /** `x`: Griff steht senkrecht, ändert eine Breite. `y`: waagerecht, Höhe. */
  axis: "x" | "y";
  /** Aktuelle Größe des Bereichs, den der Griff verändert. */
  size: number;
  /** Bereich liegt rechts/unter dem Griff — Ziehen nach links/oben vergrößert. */
  invert?: boolean;
  onResize: (next: number) => void;
  onReset?: () => void;
  className?: string;
  style?: React.CSSProperties;
}) {
  const start = useRef<{ origin: number; size: number } | null>(null);

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    start.current = { origin: axis === "x" ? event.clientX : event.clientY, size };
    document.body.style.cursor = axis === "x" ? "col-resize" : "row-resize";
    document.body.style.userSelect = "none";
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!start.current) return;
    const current = axis === "x" ? event.clientX : event.clientY;
    const delta = current - start.current.origin;
    onResize(start.current.size + (invert ? -delta : delta));
  };

  const end = (event: PointerEvent<HTMLDivElement>) => {
    if (!start.current) return;
    start.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  };

  return (
    <div
      role="separator"
      aria-orientation={axis === "x" ? "vertical" : "horizontal"}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={end}
      onPointerCancel={end}
      onDoubleClick={onReset}
      style={style}
      className={`group relative z-10 touch-none select-none ${
        axis === "x" ? "cursor-col-resize" : "cursor-row-resize"
      } ${className}`}
    >
      {/* sichtbare Linie, beim Hover/Ziehen hervorgehoben */}
      <div
        className={`absolute bg-slate-200 transition-colors group-hover:bg-slate-400 group-active:bg-slate-500 ${
          axis === "x" ? "inset-y-0 left-1/2 w-px -translate-x-1/2" : "inset-x-0 top-1/2 h-px -translate-y-1/2"
        }`}
      />
    </div>
  );
}
