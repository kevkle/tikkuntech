import type { Branch, Language, Message, Verdict } from "./types";

const BRANCHES: readonly string[] = ["belief", "grievance", "joke", "mixed", "disengage"];

export type ChatPhase = "return" | "close";

export type ChatResult = {
  // The stage of this reply, to send back with the next request.
  phase: ChatPhase | null;
  // Set when the reply was the closing message: the branch decides which extras to offer.
  menu: Branch | null;
};

export async function classifyPost(text: string): Promise<Verdict> {
  const res = await fetch("/api/classify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`classify failed: ${res.status}`);
  return res.json();
}

/**
 * Streams the assistant's next reply as plain text chunks.
 * An empty `history` asks the server for the opening message.
 * Resolves with `menu` set when the server marked this reply as the closing message.
 * Rejects on a non-200 response or a broken stream.
 */
export async function streamChat(
  post: string,
  verdict: Verdict,
  history: Message[],
  lastPhase: ChatPhase | null,
  userName: string,
  language: Language,
  onDelta: (delta: string) => void,
  signal?: AbortSignal,
): Promise<ChatResult> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      post,
      verdict,
      history: history.map(({ role, text }) => ({ role, text })),
      // The stage of the last bot message, so the server knows what comes next.
      last_phase: lastPhase,
      user_name: userName,
      language,
    }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`chat failed: ${res.status}`);

  const menuHeader = res.headers.get("x-chat-menu") ?? "";
  const menu = BRANCHES.includes(menuHeader) ? (menuHeader as Branch) : null;
  const phaseHeader = res.headers.get("x-chat-phase");
  const phase = phaseHeader === "return" || phaseHeader === "close" ? phaseHeader : null;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    onDelta(decoder.decode(value, { stream: true }));
  }
  const tail = decoder.decode();
  if (tail) onDelta(tail);
  return { phase, menu };
}
