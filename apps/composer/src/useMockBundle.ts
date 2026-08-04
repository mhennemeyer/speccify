// Hält die Mock-Closure des aktuellen Dokuments aktuell: YAML → Backend →
// kompilierte Laufzeit. Entkoppelt vom Tippen (Debounce), und ein fehlerhafter
// Zwischenstand wirft die letzte lauffähige Closure nicht weg — der Canvas
// bleibt benutzbar und markiert die Vorschau als veraltet.

import { useEffect, useRef, useState } from "react";

import { mockDraft } from "./api";
import { docToYaml } from "./doc";
import { createMockRuntime, type MockRuntime } from "./mockRuntime";
import type { SpecDoc } from "./types";

const DEBOUNCE_MS = 250;

export interface MockBundleState {
  runtime: MockRuntime | null;
  /** Modulpfad des Dokuments selbst innerhalb der Closure. */
  entry: string | null;
  /** Fehler des letzten Versuchs; `runtime` kann trotzdem (veraltet) gesetzt sein. */
  error: string | null;
  /** Die vorhandene Closure gehört nicht zum aktuellen Dokumentstand. */
  stale: boolean;
}

export function useMockBundle(doc: SpecDoc | null): MockBundleState {
  const [state, setState] = useState<MockBundleState>({
    runtime: null,
    entry: null,
    error: null,
    stale: false,
  });
  const requestRef = useRef(0);

  const yamlText = doc ? docToYaml(doc) : null;

  useEffect(() => {
    if (yamlText === null) {
      requestRef.current += 1;
      setState({ runtime: null, entry: null, error: null, stale: false });
      return;
    }
    const ticket = ++requestRef.current;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const bundle = await mockDraft(yamlText);
          if (requestRef.current !== ticket) return;
          setState({
            runtime: createMockRuntime(bundle.files),
            entry: bundle.entry,
            error: null,
            stale: false,
          });
        } catch (error) {
          if (requestRef.current !== ticket) return;
          setState((current) => ({
            ...current,
            error: String(error),
            stale: current.runtime !== null,
          }));
        }
      })();
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [yamlText]);

  return state;
}
