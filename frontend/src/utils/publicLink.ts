/** Public link a visitor opens for a form: `<origin>/f/<route>`. Empty when the form has no route yet. */
export function publicFormLink(route: string | null | undefined, origin: string): string {
  const clean = (route ?? "").trim().replace(/^\/+/, "");
  if (!clean) return "";
  // Encode each part but keep "/" so routes such as "s/something" stay intact (same as the builder header).
  const path = clean.split("/").map(encodeURIComponent).join("/");
  return `${origin.replace(/\/+$/, "")}/f/${path}`;
}

/** Copy text to the clipboard; falls back to a hidden textarea when the Clipboard API is unavailable. */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const el = document.createElement("textarea");
    el.value = text;
    el.setAttribute("readonly", "");
    el.style.position = "fixed";
    el.style.opacity = "0";
    document.body.appendChild(el);
    el.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {
      ok = false;
    }
    document.body.removeChild(el);
    return ok;
  }
}

/** "No answers yet", "1 answer", "12 answers" for the My forms card. */
export function answersLabel(count: number | null | undefined): string {
  const n = Number(count) || 0;
  return n === 0 ? "No answers yet" : n === 1 ? "1 answer" : `${n} answers`;
}
