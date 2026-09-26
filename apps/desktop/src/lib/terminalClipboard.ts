import { t } from "../i18n";
// Kopieren aus dem Agent-Terminal (Spec 068). xterm hält seine Auswahl selbst,
// der DOM hat keine — deshalb bietet das Systemmenü „Kopieren" nichts an, macOS
// quittiert ⌘C mit dem Fehlerton, und ein unbeantwortetes Tastenereignis landet
// nirgends. Die App schreibt die Auswahl daher aktiv in die Zwischenablage und
// meldet das Ereignis als erledigt. Reine Funktionen, ohne xterm-Abhängigkeit.

export type ClipboardWriter = (text: string) => Promise<void>;

/** ⌘C (macOS) bzw. Strg+Umschalt+C (Windows/Linux, wie in Terminals üblich). */
export function isCopyShortcut(event: KeyboardEvent): boolean {
  return isShortcut(event, "c");
}

/** ⌘V bzw. Strg+Umschalt+V. */
export function isPasteShortcut(event: KeyboardEvent): boolean {
  return isShortcut(event, "v");
}

function isShortcut(event: KeyboardEvent, letter: string): boolean {
  if (event.altKey || event.isComposing) return false;
  if (event.key.toLowerCase() !== letter) return false;
  return event.metaKey || (event.ctrlKey && event.shiftKey);
}

/** Ob außerhalb des Terminals eine eigene Auswahl steht, die Vorrang hat: eine
 *  DOM-Auswahl in einem anderen Element oder eine markierte Spanne in einem
 *  fremden Eingabefeld. Dann gehört ⌘C diesem Element, nicht dem Terminal. */
export function foreignSelection(active: Element | null, container: HTMLElement, doc: Document = document): boolean {
  if (active && container.contains(active)) return false;
  const dom = doc.getSelection();
  if (dom && !dom.isCollapsed && dom.anchorNode && !container.contains(dom.anchorNode)) return true;
  if (!active) return false;
  const field = active as HTMLInputElement | HTMLTextAreaElement;
  if ((field.tagName === "INPUT" || field.tagName === "TEXTAREA")
    && typeof field.selectionStart === "number" && field.selectionEnd !== field.selectionStart) {
    return true;
  }
  return false;
}

/** Schreibt in die Zwischenablage: erst der übergebene Weg (Tauri-Plugin), dann
 *  `navigator.clipboard`, zuletzt das klassische `execCommand`. Wirft nur, wenn
 *  alle drei scheitern — mit dem ersten Fehler als Ursache. */
export async function writeClipboard(text: string, primary: ClipboardWriter): Promise<void> {
  let failure: unknown = null;
  try {
    await primary(text);
    return;
  } catch (error) {
    failure = error;
  }
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
  } catch {
    // weiter zum letzten Weg
  }
  if (legacyCopy(text)) return;
  throw failure instanceof Error ? failure : new Error(String(failure ?? t("Zwischenablage nicht erreichbar")));
}

function legacyCopy(text: string): boolean {
  if (typeof document === "undefined") return false;
  const field = document.createElement("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.opacity = "0";
  document.body.appendChild(field);
  field.select();
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch {
    copied = false;
  }
  field.remove();
  return copied;
}
