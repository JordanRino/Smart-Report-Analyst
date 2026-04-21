/** Pending composer prefill until the chat shell shows the target thread. */
const PENDING_KEY = "sra:chatComposerPrefill:pending:v1";

export type PendingChatPrefill = { threadId: string; text: string };

export function stashPendingChatPrefill(threadId: string, text: string): void {
  if (typeof sessionStorage === "undefined") return;
  const payload: PendingChatPrefill = { threadId: threadId.trim(), text };
  sessionStorage.setItem(PENDING_KEY, JSON.stringify(payload));
}

export function takePendingChatPrefillForThread(threadId: string): string | null {
  if (typeof sessionStorage === "undefined") return null;
  const raw = sessionStorage.getItem(PENDING_KEY);
  if (!raw) return null;
  try {
    const p = JSON.parse(raw) as PendingChatPrefill;
    if (!p || typeof p.threadId !== "string" || typeof p.text !== "string") {
      sessionStorage.removeItem(PENDING_KEY);
      return null;
    }
    if (p.threadId !== threadId.trim()) return null;
    sessionStorage.removeItem(PENDING_KEY);
    return p.text;
  } catch {
    sessionStorage.removeItem(PENDING_KEY);
    return null;
  }
}
