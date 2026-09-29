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
export type Category =
  | "none"
  | "self_harm"
  | "violence"
  | "harassment"
  | "hate"
  | "other";

export type Verdict = {
  harmful: boolean;
  category: Category;
  severity: "low" | "medium" | "high";
  reason: string;
};
