import type { Message, Verdict } from "./types";

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
 * Rejects on a non-200 response or a broken stream.
 */
export async function streamChat(
  post: string,
  verdict: Verdict,
  history: Message[],
  onDelta: (delta: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      post,
      verdict,
      history: history.map(({ role, text }) => ({ role, text })),
    }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`chat failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    onDelta(decoder.decode(value, { stream: true }));
  }
  const tail = decoder.decode();
  if (tail) onDelta(tail);
}
