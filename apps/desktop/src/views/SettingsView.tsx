// Settings (Plan toolkit-discovery-terminal.md, T1): genau EIN Working Dir
// global, Autostart-Command für den Terminal-Agenten, und die
// Agent-Einweisungs-Dateien im Working Dir (Status + Klick-Anlage,
// niemals überschreiben).

import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { ActionButton, ErrorBox } from "../components/ui";
import { AGENT_PRESETS } from "../lib/agents";
import { useTheme } from "../lib/theme";
import ThemePicker from "../components/ThemePicker";
import { DASHBOARD_RESUME_KEY } from "../App";

interface AppSettings {
  working_dir: string | null;
  terminal_autostart_command: string;
  skill_library: string | null;
  /** Globale Skill-Quellen — gepflegt in der Bibliothek, hier nur durchgereicht. */
  skill_sources: string[];
  theme: string;
  /** Spec 030: Webhook-URL für Teamsignale — nur hier oder in SPECCIFY_WEBHOOK_URL. */
  webhook_url?: string | null;
}

interface BriefingStatus {
  id: string;
  relative_path: string;
  exists: boolean;
}

export default function SettingsView() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [briefings, setBriefings] = useState<BriefingStatus[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useTheme();
  const [resumeDashboard, setResumeDashboard] = useState(() => {
    try {
      return localStorage.getItem(DASHBOARD_RESUME_KEY) !== "0";
    } catch {
      return true;
    }
  });

  const refreshBriefings = useCallback(async (workingDir: string | null) => {
    if (!workingDir) {
      setBriefings([]);
      return;
    }
    try {
      setBriefings(
        await invoke<BriefingStatus[]>("briefing_status", { workingDir }),
      );
    } catch (e) {
      setBriefings([]);
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const loaded = await invoke<AppSettings>("get_settings");
        setSettings(loaded);
        await refreshBriefings(loaded.working_dir);
      } catch (e) {
        setError(String(e));
      }
    })();
  }, [refreshBriefings]);

  const save = async (next: AppSettings) => {
    setError(null);
    try {
      await invoke("save_settings", { settings: next });
      setSettings(next);
      setStatus("Gespeichert.");
      await refreshBriefings(next.working_dir);
    } catch (e) {
      setError(String(e));
    }
  };

  if (!settings) {
    return error ? <ErrorBox message={error} /> : <p className="text-slate-500">lädt…</p>;
  }

  return (
    <div className="max-w-xl space-y-6">
      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Erscheinungsbild</h3>
        <p className="mb-2 text-sm text-slate-600">
          Hell, dunkel oder wie das System — gilt für Dashboard und alle
          Projektfenster.
        </p>
        <ThemePicker value={theme} onChange={(next) => void setTheme(next)} />
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Agent-Sitzung</h3>
        <label className="flex items-start gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={resumeDashboard}
            onChange={(e) => {
              setResumeDashboard(e.target.checked);
              try {
                localStorage.setItem(DASHBOARD_RESUME_KEY, e.target.checked ? "1" : "0");
              } catch {
                // dito
              }
            }}
            className="mt-1"
          />
          <span>
            Das Dashboard-Terminal setzt nach einem Neustart genau die gemerkte Sitzung
            fort (<code>claude --resume &lt;id&gt;</code>). Ohne bekannte Sitzungs-ID fragt
            die Seitenleiste ausdrücklich nach. Projektfenster haben denselben Schalter
            in ihren Einstellungen.
          </span>
        </label>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Teamsignale</h3>
        <p className="mb-2 text-sm text-slate-600">
          Webhook-URL (Slack, Teams, Mattermost) für Nachrichten aus Projekten, die den Webhook in
          ihren Einstellungen aktiviert haben. Bleibt auf diesem Rechner; alternativ die
          Umgebungsvariable <code>SPECCIFY_WEBHOOK_URL</code>.
        </p>
        <input
          aria-label="Webhook-URL"
          value={settings.webhook_url ?? ""}
          onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value || null })}
          onBlur={() => void save(settings)}
          placeholder="https://hooks.slack.com/services/…"
          className="mb-6 w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm"
          spellCheck={false}
        />
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Working Dir</h3>
        <p className="mb-2 text-sm text-slate-600">
          Hier landen eigene Tools/MCPs (<code>.speccify/toolbox/</code>) und
          Aktionen; der Terminal-Agent startet in diesem Verzeichnis.
        </p>
        <div className="flex gap-2">
          <input
            value={settings.working_dir ?? ""}
            onChange={(e) =>
              setSettings({ ...settings, working_dir: e.target.value || null })
            }
            placeholder="~/speccify-work"
            className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm"
            spellCheck={false}
          />
          <button
            onClick={async () => {
              const picked = await open({ directory: true, title: "Working Dir wählen" });
              if (typeof picked === "string") {
                await save({ ...settings, working_dir: picked });
              }
            }}
            className="shrink-0 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            Auswählen…
          </button>
        </div>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Skill-Quellen</h3>
        <p className="text-sm text-slate-600">
          Repos und Ordner, aus denen Projekte Skills importieren, verwaltest Du
          unter <strong>Bibliothek</strong> (Git-URL oder Ordner, global für alle
          Projekte). Projekte binden im Skills-Tab weitere Quellen an.
          {settings.skill_sources.length > 0
            ? ` Aktuell: ${settings.skill_sources.length} Quelle${settings.skill_sources.length === 1 ? "" : "n"}.`
            : ""}
        </p>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Terminal-Agent</h3>
        <label className="mb-1 block text-xs font-medium text-slate-500">
          Autostart-Command (läuft beim Öffnen der Terminal-Seitenleiste)
        </label>
        <input
          value={settings.terminal_autostart_command}
          onChange={(e) =>
            setSettings({ ...settings, terminal_autostart_command: e.target.value })
          }
          className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm"
          spellCheck={false}
        />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {AGENT_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() =>
                setSettings({ ...settings, terminal_autostart_command: preset.command })
              }
              className={`rounded border px-2 py-1 text-xs ${
                settings.terminal_autostart_command === preset.command
                  ? "border-slate-700 bg-slate-700 text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </section>

      <ActionButton
        onClick={() => save(settings)}
        className="bg-slate-800 text-white hover:bg-slate-700"
      >
        Speichern
      </ActionButton>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">
          Agent-Einweisung im Working Dir
        </h3>
        {!settings.working_dir ? (
          <p className="text-sm text-slate-500">
            Erst ein Working Dir wählen und speichern.
          </p>
        ) : (
          <div className="space-y-2">
            {briefings.map((briefing) => (
              <div
                key={briefing.id}
                className="flex items-center justify-between rounded border border-slate-200 bg-white px-3 py-2 text-sm"
              >
                <span className="font-mono">{briefing.relative_path}</span>
                {briefing.exists ? (
                  <span className="text-emerald-600">vorhanden ✓</span>
                ) : (
                  <ActionButton
                    onClick={async () => {
                      setError(null);
                      try {
                        const created = await invoke<string>("create_briefing_file", {
                          workingDir: settings.working_dir,
                          id: briefing.id,
                        });
                        setStatus(`Angelegt: ${created}`);
                        await refreshBriefings(settings.working_dir);
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    anlegen
                  </ActionButton>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {status ? <p className="text-xs text-slate-500">{status}</p> : null}
      {error ? <ErrorBox message={error} /> : null}
    </div>
  );
}
