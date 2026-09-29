import type { Branch } from "./types";

/* ==========================================================================
   Content for the option menu shown after a few turns of chat.
   Edit this file to change what is offered; no component code needs to change.
   ========================================================================== */

export type ResourceKind = "learn" | "talk";

export type Resource = {
  title: string;
  blurb: string;
  // null = placeholder, rendered as text with no link.
  url: string | null;
};

export const KIND_LABELS: Record<ResourceKind, string> = {
  learn: "Learn more",
  talk: "Talk with people",
};

// Extras offered next to "Edit my post" and "Post it as is", in order, per routed branch.
// "disengage" never gets a menu.
export const MENU_EXTRAS: Record<Branch, ResourceKind[]> = {
  belief: ["learn", "talk"],
  grievance: ["talk", "learn"],
  joke: ["learn"],
  mixed: ["learn"],
  disengage: [],
};

// TODO: replace these placeholders with a human-curated, dated list. Before adding an
// entry, check that the organization is still active and that the link works.
export const RESOURCES: Record<ResourceKind, Resource[]> = {
  learn: [
    {
      title: "Curated reading coming soon",
      blurb:
        "Short, non-judgmental explainers on how this kind of language lands. Nothing is required.",
      url: null,
    },
  ],
  talk: [
    {
      title: "Curated communities coming soon",
      blurb:
        "Facilitated conversations and support groups you can join if you want to. Nothing is required.",
      url: null,
    },
  ],
};
