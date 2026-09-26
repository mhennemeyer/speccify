import { useTerminalPreferences } from "../lib/terminalPreferences";
import { invoke } from "@tauri-apps/api/core";
import { useState } from "react";
import { t } from "../i18n";

export default function TerminalPreferencesEditor() {
  const { preferences, update, error } = useTerminalPreferences();
  const [notificationStatus, setNotificationStatus] = useState("");
  return <div className="my-3 space-y-2 text-xs text-slate-600">
    <label className="flex items-center gap-2">{t("Terminal-Schriftgröße")}
      <select aria-label={t("Terminal-Schriftgröße")} value={preferences.font_size}
        className="rounded border border-slate-300 bg-white px-2 py-1"
        onChange={e => void update({ font_size: Number(e.target.value) })}>
        {Array.from({ length: 25 }, (_, i) => i + 8).map(n => <option key={n} value={n}>{n} px</option>)}
      </select>
    </label>
    <p>{t("Gilt sofort für alle Fenster. Standard: 14 px. Die Farben folgen dem Erscheinungsbild.")}</p>
    <label className="flex items-center gap-2"><input type="checkbox" checked={preferences.popups}
      onChange={e => void update({ popups: e.target.checked })} />{t("Rückfragen als Popup anzeigen")}</label>
    <label className="flex items-center gap-2"><input type="checkbox" checked={preferences.system_notifications}
      onChange={e => void update({ system_notifications: e.target.checked })} />{t("Systemmeldungen bei inaktivem Fenster")}</label>
    <p>{t("Reagiert auf Terminal-Signale und erkannte Freigabefragen. Antworten erfolgen im Terminal. Freie Textfragen werden nicht immer erkannt. Systemmeldungen benötigen die Erlaubnis des Betriebssystems; auf Windows die installierte App verwenden.")}</p>
    <label className="flex items-center gap-2"><input type="checkbox" checked={preferences.persist_sessions}
      onChange={e => void update({ persist_sessions: e.target.checked })} />{t("Terminals überleben App-Neustarts")}</label>
    <p>{t("Neue Terminals laufen dann in einem eigenen Host-Prozess. Wird die App beendet oder neu gebaut, läuft der Agent weiter; das Fenster hängt sich beim nächsten Start wieder an und zeigt die bisherige Ausgabe. Fenster schließen oder")}{" "}<em>{t("Neu starten")}</em>{" "}{t("beenden die Sitzung weiterhin. Gilt für Terminals, die nach dem Einschalten gestartet werden.")}</p>
    <button className="rounded border px-2 py-1" onClick={() => {
      void invoke("terminal_notification_test").then(() => setNotificationStatus(t("Test gesendet. Falls nichts erscheint, Speccify in den Mitteilungseinstellungen des Systems erlauben.")))
        .catch(error => setNotificationStatus(String(error)));
    }}>{t("Systemmeldung testen")}</button>
    {notificationStatus && <p role="status">{notificationStatus}</p>}
    {error && <p role="alert" className="text-red-600">{error}</p>}
  </div>;
}
