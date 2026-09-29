export type Post = {
  id: number;
  author: string;
  handle: string;
  time: string;
  text: string;
};

export type Message = {
  id: number;
  role: "ai" | "user";
  text: string;
};

// Mirrors backend/app/schemas.py Verdict
export type Verdict = {
  harmful: boolean;
  category: string;
  severity: "low" | "medium" | "high";
  reason: string;
};
