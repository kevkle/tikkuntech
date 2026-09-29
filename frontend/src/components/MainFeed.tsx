"use client";

import { useState } from "react";
import type { Post } from "@/lib/types";

/* ==========================================================================
   COMPONENT 1: MainFeed
   Presentational only. Backend hookup points:
     - `posts`          -> array from your "get posts" endpoint
     - `onPostClick`    -> called with the draft text when "Post" is clicked
   ========================================================================== */

const DUMMY_POSTS: Post[] = [
  {
    id: 1,
    author: "Maya Okafor",
    handle: "@maya",
    time: "2h",
    text: "Finished my first trail run of the season. Legs are jelly, mood is great.",
  },
  {
    id: 2,
    author: "Jonas Weber",
    handle: "@jonasw",
    time: "5h",
    text: "Hot take: the best debugging tool is still a walk around the block.",
  },
];

type MainFeedProps = {
  posts?: Post[];
  onPostClick?: (draft: string) => void;
};

export function MainFeed({
  posts = DUMMY_POSTS,
  onPostClick = () => {},
}: MainFeedProps) {
  const [draft, setDraft] = useState("");

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto max-w-2xl px-4 py-3 text-lg font-semibold text-slate-800">
          Home
        </div>
      </header>

      <main className="mx-auto max-w-2xl space-y-4 px-4 py-6">
        {/* Create Post box */}
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            placeholder="What's on your mind?"
            className="w-full resize-none rounded-lg border border-slate-200 p-3 text-slate-800 placeholder-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
          <div className="mt-3 flex justify-end">
            <button
              onClick={() => onPostClick(draft)}
              className="rounded-full bg-indigo-600 px-6 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-300"
            >
              Post
            </button>
          </div>
        </section>

        {/* Posts */}
        {posts.map((post) => (
          <article
            key={post.id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-700">
                {post.author.charAt(0)}
              </div>
              <div className="text-sm">
                <span className="font-semibold text-slate-800">{post.author}</span>{" "}
                <span className="text-slate-500">
                  {post.handle} &middot; {post.time}
                </span>
              </div>
            </div>
            <p className="mt-3 text-slate-700">{post.text}</p>
          </article>
        ))}
      </main>
    </div>
  );
}
