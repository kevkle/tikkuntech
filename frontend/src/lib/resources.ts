import type { Branch } from "./types";

/* ==========================================================================
   Content for the option menu shown after a few turns of chat.
   Edit this file to change what is offered; no component code needs to change.
   The words on screen (labels, titles, blurbs) live in messages/<language>.json under
   "resources", keyed by kind and entry id. This file holds the structure and the links.
   ========================================================================== */

export type ResourceKind = "learn" | "talk";

export type Resource = {
  // Names the entry's title and blurb in messages/<language>.json.
  id: string;
  // null = placeholder, rendered as text with no link.
  url: string | null;
};

// Extras offered next to "Edit my post" and "Post it as is", in order, per routed branch.
// "disengage" never gets a menu.
export const MENU_EXTRAS: Record<Branch, ResourceKind[]> = {
  default: ["learn", "talk"],
  disengage: [],
};

// TODO: replace these placeholders with a human-curated, dated list. Before adding an
// entry, check that the organization is still active and that the link works. Add each
// entry's title and blurb to every language file.
export const RESOURCES: Record<ResourceKind, Resource[]> = {
  learn: [{ id: "placeholder", url: null }],
  talk: [{ id: "placeholder", url: null }],
};
