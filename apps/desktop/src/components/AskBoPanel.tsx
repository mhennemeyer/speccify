// ask_bo-Interaktionen (T7): rendert die vom Agent gestellten Fragen —
// buttons (Einzelauswahl), multi_select (Checkboxen + OK), form
// (Fragenliste; leere Eingabe ⇒ Empfehlung gilt). Beantwortete Elemente
// frieren ein (iKanbanAi-Semantik).

import { useState } from "react";

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
  return (
    <div className="max-h-[45%] shrink-0 space-y-2 overflow-y-auto border-b border-slate-700 bg-slate-800 p-2">
      {interactions.map((interaction) => (
        <InteractionCard
          key={interaction.id}
          interaction={interaction}
          onAnswer={onAnswer}
        />
      ))}
    </div>
  );
}

function InteractionCard({
  interaction,
  onAnswer,
}: {
  interaction: AskBoInteraction;
  onAnswer: AskBoPanelProps["onAnswer"];
}) {
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [values, setValues] = useState<string[]>(
    () => interaction.fields.map(() => ""),
  );
  const done = interaction.answered !== undefined;

  return (
    <div
      className={`rounded border border-slate-600 bg-slate-900 p-2 text-sm ${
        done ? "opacity-60" : ""
      }`}
    >
      <p className="mb-2 font-medium text-slate-200">{interaction.prompt}</p>

      {interaction.kind === "buttons" ? (
        <div className="flex flex-wrap gap-1.5">
          {interaction.options.map((option) => {
            const selected = interaction.answered?.selectedOptions.includes(option);
            return (
              <button
                key={option}
                disabled={done}
                onClick={() => onAnswer(interaction.id, [option], [])}
                className={`rounded px-2.5 py-1 text-xs ${
                  selected
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-700 text-slate-200 hover:bg-slate-600 disabled:hover:bg-slate-700"
                }`}
              >
                {option}
              </button>
            );
          })}
        </div>
      ) : null}

      {interaction.kind === "multi_select" ? (
        <div className="space-y-1">
          {interaction.options.map((option) => {
            const selected = done
              ? interaction.answered!.selectedOptions.includes(option)
              : checked.has(option);
            return (
              <label key={option} className="flex items-center gap-2 text-xs text-slate-200">
                <input
                  type="checkbox"
                  disabled={done}
                  checked={selected}
                  onChange={(event) => {
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
            <button
              onClick={() =>
                onAnswer(
                  interaction.id,
                  interaction.options.filter((option) => checked.has(option)),
                  [],
                )
              }
              className="mt-1 rounded bg-slate-700 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-600"
            >
              OK
            </button>
          ) : null}
        </div>
      ) : null}

      {interaction.kind === "form" ? (
        <div className="space-y-1.5">
          {interaction.fields.map((field, index) => (
            <div key={index}>
              <label className="mb-0.5 block text-[11px] text-slate-400">
                {field.label}
              </label>
              <input
                disabled={done}
                value={done ? interaction.answered!.fieldValues[index] ?? "" : values[index]}
                placeholder={field.recommended ?? ""}
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
            <button
              onClick={() =>
                onAnswer(
                  interaction.id,
                  [],
                  // Leere Eingabe ⇒ Empfehlung gilt (iKanbanAi-Semantik).
                  values.map((value, index) =>
                    value.trim() === ""
                      ? (interaction.fields[index]?.recommended ?? "")
                      : value,
                  ),
                )
              }
              className="mt-1 rounded bg-slate-700 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-600"
            >
              Antworten senden
            </button>
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
