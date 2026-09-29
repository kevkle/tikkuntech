import type { Verdict } from "./types";

export async function classifyPost(text: string): Promise<Verdict> {
  const res = await fetch("/api/classify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`classify failed: ${res.status}`);
  return res.json();
}
