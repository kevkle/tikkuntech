"use client";

import { Heart, MessageCircle, MoreHorizontal, Repeat, Share } from "lucide-react";
import { useTranslations } from "next-intl";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import type { Post } from "@/lib/types";

/* ==========================================================================
   COMPONENT 1: MainFeed
   Presentational only. Backend hookup points:
     - `posts`          -> array from your "get posts" endpoint
     - `onPostClick`    -> called with the draft text when "Post" is clicked
   ========================================================================== */

export const DUMMY_POSTS: Post[] = [
  {
    id: 1,
    author: "Maya Okafor",
    handle: "@maya",
    time: "2h",
    text: "Finished my first trail run of the season. Legs are jelly, mood is great.",
    colorClass: "bg-emerald-100 text-emerald-700",
  },
  {
    id: 2,
    author: "Jonas Weber",
    handle: "@jonasw",
    time: "5h",
    text: "Hot take: the best debugging tool is still a walk around the block.",
    colorClass: "bg-blue-100 text-blue-700",
  },
];

const DEFAULT_AVATAR_CLASS = "bg-indigo-100 text-indigo-700";

type MainFeedProps = {
  posts?: Post[];
  draft: string;
  onDraftChange: (draft: string) => void;
  onPostClick?: (draft: string) => void;
  isPosting?: boolean;
  error?: string | null;
};

export function MainFeed({
  posts = DUMMY_POSTS,
  draft,
  onDraftChange,
  onPostClick = () => {},
  isPosting = false,
  error = null,
}: MainFeedProps) {
  const t = useTranslations("feed");
  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-bold text-slate-900">{t("home")}</h1>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">
              {t("you")}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
        {/* Create Post box */}
        <section className="mb-8 flex gap-4 border-b border-slate-200 pb-6">
          <div className="hidden h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-slate-900 font-bold text-white sm:flex">
            {t("you")}
          </div>
          <div className="flex-1">
            <textarea
              value={draft}
              onChange={(e) => onDraftChange(e.target.value)}
              rows={3}
              placeholder={t("placeholder")}
              className="w-full resize-none bg-transparent text-lg text-slate-900 placeholder-slate-500 focus:outline-none"
            />
            {error && (
              <p role="alert" className="mt-2 text-sm text-rose-600">
                {error}
              </p>
            )}
            <div className="mt-2 flex items-center justify-end border-t border-slate-100 pt-3">
              <button
                onClick={() => onPostClick(draft)}
                disabled={isPosting || !draft.trim()}
                className="rounded-full bg-slate-900 px-6 py-2 text-sm font-bold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:opacity-50"
              >
                {t("post")}
              </button>
            </div>
          </div>
        </section>

        {/* Posts */}
        <div className="divide-y divide-slate-200">
          {posts.map((post) => (
            <article key={post.id} className="py-6 transition hover:bg-slate-100/50">
              <div className="flex gap-4">
                <div
                  className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full font-bold ${
                    post.colorClass ?? DEFAULT_AVATAR_CLASS
                  }`}
                >
                  {post.author.charAt(0)}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-[15px]">
                      <span className="cursor-pointer font-bold text-slate-900 hover:underline">
                        {post.author}
                      </span>
                      <span className="text-slate-500">{post.handle}</span>
                      <span className="text-slate-500">·</span>
                      <span className="cursor-pointer text-slate-500 hover:underline">
                        {post.time}
                      </span>
                    </div>
                    <button aria-label={t("more")} className="text-slate-400 hover:text-slate-900">
                      <MoreHorizontal size={18} />
                    </button>
                  </div>
                  <p className="mt-1.5 whitespace-pre-wrap text-[15px] leading-relaxed text-slate-900">
                    {post.text}
                  </p>
                  <div className="mt-4 flex max-w-md items-center justify-between text-slate-500">
                    <button aria-label={t("reply")} className="group flex items-center gap-2 hover:text-blue-500">
                      <div className="rounded-full p-2 group-hover:bg-blue-50">
                        <MessageCircle size={18} />
                      </div>
                    </button>
                    <button aria-label={t("repost")} className="group flex items-center gap-2 hover:text-emerald-500">
                      <div className="rounded-full p-2 group-hover:bg-emerald-50">
                        <Repeat size={18} />
                      </div>
                    </button>
                    <button aria-label={t("like")} className="group flex items-center gap-2 hover:text-rose-500">
                      <div className="rounded-full p-2 group-hover:bg-rose-50">
                        <Heart size={18} />
                      </div>
                    </button>
                    <button aria-label={t("share")} className="group flex items-center gap-2 hover:text-blue-500">
                      <div className="rounded-full p-2 group-hover:bg-blue-50">
                        <Share size={18} />
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      </main>
    </div>
  );
}
