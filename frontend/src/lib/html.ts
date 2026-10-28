/**
 * Escape text before interpolating it into an HTML string.
 *
 * Print windows opened with `window.open('')` share this app's origin, so any
 * unescaped item name / SKU / barcode written with `document.write` would run
 * as script with the current user's session.
 */
export function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
