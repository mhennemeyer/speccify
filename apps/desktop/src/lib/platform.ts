// Plattform-Erkennung fürs Layout (W7d). Auf macOS laufen die Fenster mit
// transparenter Titelleiste (Tauri `titleBarStyle: Overlay`): die Ampel
// schwebt oben links über dem Inhalt, also braucht die erste Zeile links
// Platz und muss als Drag-Region dienen. Windows behält seine native
// Titelleiste — dort ist nichts zu tun.

export const isMac = /Mac|iPhone|iPad/.test(navigator.platform) || /Macintosh/.test(navigator.userAgent);

/** Platz für die macOS-Ampel in der obersten Zeile (px). */
export const TRAFFIC_LIGHT_INSET = isMac ? 78 : 0;
