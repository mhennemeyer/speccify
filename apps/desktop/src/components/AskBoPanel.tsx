// ask_bo-Interaktionen (T7): rendert die vom Agent gestellten Fragen —
// buttons (Einzelauswahl), multi_select (Checkboxen + OK), form
// (Fragenliste; leere Eingabe ⇒ Empfehlung gilt). Beantwortete Elemente
// frieren ein (iKanbanAi-Semantik).
//
// Tastatur (BO-Finding): die neueste offene Frage bekommt den Fokus.
// buttons: ←/→ (oder ↑/↓) bewegt die Auswahl (Start = erste Option =
// Empfehlung), Enter wählt, Ziffern wählen direkt. multi_select: ↑/↓ +
// Space toggelt, Enter sendet. form: Enter springt weiter / sendet am Ende.

import { useEffect, useRef, useState } from "react";

export interface AskBoField {
  label: string;
  recommended: string | null;
}

export interface AskBoInteraction {
  id: string;
  kind: "buttons" | "multi_select" | "form" | string;
  prompt: string;
  options: string[];
  fields: AskBoField[];
  answered?: { selectedOptions: string[]; fieldValues: string[] };
}

interface AskBoPanelProps {
  interactions: AskBoInteraction[];
  onAnswer: (id: string, selectedOptions: string[], fieldValues: string[]) => void;
}

export default function AskBoPanel({ interactions, onAnswer }: AskBoPanelProps) {
  if (interactions.length === 0) return null;
  const lastOpen = [...interactions].reverse().find((entry) => !entry.answered);
  return (
    <div className="max-h-[45%] shrink-0 space-y-2 overflow-y-auto border-b border-slate-700 bg-slate-800 p-2">
      {interactions.map((interaction) => (
        <InteractionCard
          key={interaction.id}
          interaction={interaction}
          autoFocus={interaction.id === lastOpen?.id}
          onAnswer={onAnswer}
        />
      ))}
    </div>
  );
}

function InteractionCard({
  interaction,
  autoFocus,
  onAnswer,
}: {
  interaction: AskBoInteraction;
  autoFocus: boolean;
  onAnswer: AskBoPanelProps["onAnswer"];
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [cursor, setCursor] = useState(0);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [values, setValues] = useState<string[]>(() => interaction.fields.map(() => ""));
  const done = interaction.answered !== undefined;

  useEffect(() => {
    if (autoFocus && !done) cardRef.current?.focus();
  }, [autoFocus, done]);

  const submitMultiSelect = () =>
    onAnswer(
      interaction.id,
      interaction.options.filter((option) => checked.has(option)),
      [],
    );

  const submitForm = () =>
    onAnswer(
      interaction.id,
      [],
      // Leere Eingabe ⇒ Empfehlung gilt (iKanbanAi-Semantik).
      values.map((value, index) =>
        value.trim() === "" ? (interaction.fields[index]?.recommended ?? "") : value,
      ),
    );

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (done) return;
    const count = interaction.options.length;
    const isChoice = interaction.kind === "buttons" || interaction.kind === "multi_select";
    if (!isChoice || count === 0) return;

    if (["ArrowLeft", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      setCursor((current) => (current - 1 + count) % count);
    } else if (["ArrowRight", "ArrowDown"].includes(event.key)) {
      event.preventDefault();
      setCursor((current) => (current + 1) % count);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (interaction.kind === "buttons") {
        onAnswer(interaction.id, [interaction.options[cursor]], []);
      } else {
        submitMultiSelect();
      }
    } else if (event.key === " " && interaction.kind === "multi_select") {
      event.preventDefault();
      const option = interaction.options[cursor];
      setChecked((current) => {
        const next = new Set(current);
        if (next.has(option)) next.delete(option);
        else next.add(option);
        return next;
      });
    } else if (/^[1-9]$/.test(event.key)) {
      const index = Number(event.key) - 1;
      if (index < count) {
        event.preventDefault();
        if (interaction.kind === "buttons") {
          onAnswer(interaction.id, [interaction.options[index]], []);
        } else {
          setCursor(index);
        }
      }
    }
  };

  return (
    <div
      ref={cardRef}
      tabIndex={done ? -1 : 0}
      onKeyDown={handleKeyDown}
      className={`rounded border border-slate-600 bg-slate-900 p-2 text-sm outline-none focus:border-emerald-500 ${
        done ? "opacity-60" : ""
      }`}
    >
      <p className="mb-2 font-medium text-slate-200">{interaction.prompt}</p>

      {interaction.kind === "buttons" ? (
        <>
          <div className="flex flex-wrap gap-1.5">
            {interaction.options.map((option, index) => {
              const selected = interaction.answered?.selectedOptions.includes(option);
              const focused = !done && index === cursor;
              return (
                <button
                  key={option}
                  disabled={done}
                  tabIndex={-1}
                  onClick={() => onAnswer(interaction.id, [option], [])}
                  className={`rounded px-2.5 py-1 text-xs ${
                    selected
                      ? "bg-emerald-600 text-white"
                      : focused
                        ? "bg-slate-600 text-white ring-1 ring-emerald-400"
                        : "bg-slate-700 text-slate-200 hover:bg-slate-600 disabled:hover:bg-slate-700"
                  }`}
                >
                  {option}
                </button>
              );
            })}
          </div>
          {!done ? (
            <p className="mt-1 text-[10px] text-slate-500">←/→ wählen · Enter bestätigen</p>
          ) : null}
        </>
      ) : null}

      {interaction.kind === "multi_select" ? (
        <div className="space-y-1">
          {interaction.options.map((option, index) => {
            const selected = done
              ? interaction.answered!.selectedOptions.includes(option)
              : checked.has(option);
            const focused = !done && index === cursor;
            return (
              <label
                key={option}
                className={`flex items-center gap-2 rounded px-1 text-xs text-slate-200 ${
                  focused ? "bg-slate-700 ring-1 ring-emerald-400" : ""
                }`}
              >
                <input
                  type="checkbox"
                  disabled={done}
                  tabIndex={-1}
                  checked={selected}
                  onChange={(event) => {
                    setCursor(index);
                    setChecked((current) => {
                      const next = new Set(current);
                      if (event.target.checked) next.add(option);
                      else next.delete(option);
                      return next;
                    });
                  }}
                />
                {option}
              </label>
            );
          })}
          {!done ? (
            <div className="mt-1 flex items-center gap-2">
              <button
                onClick={submitMultiSelect}
                tabIndex={-1}
                className="rounded bg-slate-700 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-600"
              >
                OK
              </button>
              <span className="text-[10px] text-slate-500">
                ↑/↓ wählen · Space an/aus · Enter senden
              </span>
            </div>
          ) : null}
        </div>
      ) : null}

      {interaction.kind === "form" ? (
        <div className="space-y-1.5">
          {interaction.fields.map((field, index) => (
            <div key={index}>
              <label className="mb-0.5 block text-[11px] text-slate-400">{field.label}</label>
              <input
                disabled={done}
                autoFocus={autoFocus && !done && index === 0}
                data-askbo-field={`${interaction.id}-${index}`}
                value={done ? (interaction.answered!.fieldValues[index] ?? "") : values[index]}
                placeholder={field.recommended ?? ""}
                onKeyDown={(event) => {
                  if (event.key !== "Enter") return;
                  event.preventDefault();
                  // Enter: nächstes Feld fokussieren, am Ende senden
                  // (leere Felder = Empfehlung, iKanbanAi-Return-Semantik).
                  const next = document.querySelector<HTMLInputElement>(
                    `[data-askbo-field="${interaction.id}-${index + 1}"]`,
                  );
                  if (next) next.focus();
                  else submitForm();
                }}
                onChange={(event) =>
                  setValues((current) =>
                    current.map((value, i) => (i === index ? event.target.value : value)),
                  )
                }
                className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs text-slate-100"
              />
            </div>
          ))}
          {!done ? (
            <div className="mt-1 flex items-center gap-2">
              <button
                onClick={submitForm}
                tabIndex={-1}
                className="rounded bg-slate-700 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-600"
              >
                Antworten senden
              </button>
              <span className="text-[10px] text-slate-500">
                Enter = weiter/senden · leer = Empfehlung gilt
              </span>
            </div>
          ) : null}
        </div>
      ) : null}

      {!["buttons", "multi_select", "form"].includes(interaction.kind) ? (
        <p className="text-xs text-amber-400">
          Unbekannte Interaktions-Art „{interaction.kind}" — App aktualisieren.
        </p>
      ) : null}

      {done ? <p className="mt-1 text-[10px] text-emerald-500">beantwortet ✓</p> : null}
    </div>
  );
}
