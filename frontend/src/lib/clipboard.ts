/**
 * Copy text to the clipboard, including on plain-HTTP LAN deployments.
 *
 * `navigator.clipboard` only exists in secure contexts (HTTPS or localhost).
 * The default deployment is `http://<NAS IP>:3000`, where it is `undefined`,
 * so a bare `navigator.clipboard.writeText()` throws and nothing is copied.
 * This falls back to the legacy `execCommand('copy')` path.
 *
 * Returns true when the text was copied; callers should show the text for
 * manual copying when it returns false.
 */
export async function copyText(text: string): Promise<boolean> {
  if (typeof window === 'undefined') return false;

  if (window.isSecureContext && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Permission denied or document not focused: try the legacy path.
    }
  }

  return legacyCopy(text);
}

function legacyCopy(text: string): boolean {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  // Keep it off-screen but focusable; iOS needs a non-zero font size to
  // avoid zooming in.
  textarea.style.position = 'fixed';
  textarea.style.top = '0';
  textarea.style.left = '-9999px';
  textarea.style.opacity = '0';
  textarea.style.fontSize = '16px';

  // Radix dialogs trap focus. A textarea appended to <body> outside the open
  // dialog cannot receive focus, so the selection (and copy) would be empty.
  const host =
    (document.activeElement?.closest('[role="dialog"], [role="alertdialog"]') as HTMLElement | null) ??
    document.body;
  const previousFocus = document.activeElement as HTMLElement | null;

  host.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, text.length);

  let ok = false;
  try {
    ok = document.execCommand('copy');
  } catch {
    ok = false;
  }

  host.removeChild(textarea);
  previousFocus?.focus?.();
  return ok;
}
