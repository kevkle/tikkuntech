"use client";

import { useEffect, useRef, useState } from "react";
import { KIND_LABELS, MENU_EXTRAS, RESOURCES, type ResourceKind } from "@/lib/resources";
import type { Branch, Message } from "@/lib/types";

/* ==========================================================================
   COMPONENT 2: InterventionModal
   Overlay chat. Presentational: the parent owns the conversation.
     - `isOpen`          -> controlled by parent
     - `messages`        -> the conversation so far (assistant text streams in)
     - `isStreaming`     -> true while a reply is arriving; input is disabled
     - `chatError`       -> shown under the chat if a reply failed
     - `menuBranch`      -> set once the menu message has arrived; shows the option buttons
     - `onSendMessage`   -> called with the user's reply text (typed or a quick reply)
     - `onDeletePost`, `onPublishAnyway` -> button handlers
     - `onClose` -> exit without deleting or publishing (back to editing)
   ========================================================================== */

// One-tap starters shown before the person has replied. They are sent like typed text.
const QUICK_REPLIES = ["I'm just angry", "I meant it", "Why do you care?", "It's just a joke"];

type InterventionModalProps = {
  isOpen?: boolean;
  messages?: Message[];
  isStreaming?: boolean;
  chatError?: string | null;
  menuBranch?: Branch | null;
  onSendMessage?: (text: string) => void;
  onDeletePost?: () => void;
  onPublishAnyway?: () => void;
  onClose?: () => void;
};

export function InterventionModal({
  isOpen = false,
  messages = [],
  isStreaming = false,
  chatError = null,
  menuBranch = null,
  onSendMessage = () => {},
  onDeletePost = () => {},
  onPublishAnyway = () => {},
  onClose = () => {},
}: InterventionModalProps) {
  const [input, setInput] = useState("");
  const [openPanel, setOpenPanel] = useState<ResourceKind | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, chatError, menuBranch, openPanel]);

  // A closed modal stays mounted, so forget which panel was open.
  useEffect(() => {
    if (!isOpen) setOpenPanel(null);
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSend = (raw: string) => {
    const text = raw.trim();
    if (!text || isStreaming) return;
    setInput("");
    onSendMessage(text);
  };

  const last = messages[messages.length - 1];
  const openingArrived = last?.role === "ai" && last.text !== "";
  const showQuickReplies =
    openingArrived && !isStreaming && !messages.some((m) => m.role === "user");
  const showMenu = menuBranch !== null && !isStreaming;
  const extras = menuBranch ? MENU_EXTRAS[menuBranch] : [];
  const optionClass =
    "rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-slate-200 backdrop-blur-md transition hover:border-indigo-300/50 hover:bg-white/15 hover:text-white";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 p-4 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
    >
      <div className="flex h-[85vh] max-h-full w-full max-w-3xl flex-col overflow-hidden rounded-3xl border border-white/10 bg-slate-800/60 shadow-[0_25px_80px_-10px_rgba(0,0,0,0.7)] backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 text-sm font-semibold text-white">
              AI
            </div>
            <div>
              <div className="text-sm font-semibold text-white">Before you post</div>
              <div className="text-xs text-slate-400">A quick check-in</div>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close and keep editing my post"
            className="flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition hover:bg-white/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-indigo-300/50"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        {/* Chat window */}
        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
          {messages.map((m) => {
            const waiting = m.role === "ai" && m.text === "" && isStreaming;
            return (
              <div
                key={m.id}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {waiting ? (
                  <div
                    role="status"
                    aria-label="Assistant is typing"
                    className="flex items-center gap-1.5 rounded-3xl rounded-bl-lg border border-white/10 bg-white/10 px-5 py-4 backdrop-blur-md"
                  >
                    {[0, 150, 300].map((delay) => (
                      <span
                        key={delay}
                        className="h-2 w-2 animate-bounce rounded-full bg-slate-300"
                        style={{ animationDelay: `${delay}ms` }}
                      />
                    ))}
                  </div>
                ) : (
                  <div
                    className={`max-w-[75%] whitespace-pre-wrap rounded-3xl px-5 py-3 text-[15px] leading-relaxed shadow-lg ${
                      m.role === "user"
                        ? "rounded-br-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white"
                        : "rounded-bl-lg border border-white/10 bg-white/10 text-slate-100 backdrop-blur-md"
                    }`}
                  >
                    {m.text}
                  </div>
                )}
              </div>
            );
          })}
          {chatError && (
            <p role="alert" className="text-sm text-rose-300">
              {chatError}
            </p>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Quick replies */}
        {showQuickReplies && (
          <div className="flex flex-wrap gap-2 px-6 pb-3">
            {QUICK_REPLIES.map((label) => (
              <button
                key={label}
                onClick={() => handleSend(label)}
                className={optionClass}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {/* Option menu: shown after the fixed menu message. All options carry equal weight. */}
        {showMenu && (
          <div className="px-6 pb-3">
            <div className="flex flex-wrap gap-2">
              <button onClick={onClose} className={optionClass}>
                Edit my post
              </button>
              <button onClick={onPublishAnyway} className={optionClass}>
                Post it as is
              </button>
              {extras.map((kind) => (
                <button
                  key={kind}
                  onClick={() => setOpenPanel(openPanel === kind ? null : kind)}
                  aria-expanded={openPanel === kind}
                  className={optionClass}
                >
                  {KIND_LABELS[kind]}
                </button>
              ))}
            </div>
            {openPanel && (
              <div className="mt-3 space-y-2 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
                {RESOURCES[openPanel].map((r) => (
                  <div key={r.title}>
                    {r.url ? (
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-indigo-300 underline"
                      >
                        {r.title}
                      </a>
                    ) : (
                      <span className="font-semibold text-white">{r.title}</span>
                    )}
                    <p className="text-slate-300">{r.blurb}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Chat input */}
        <div className="flex gap-3 border-t border-white/10 px-6 py-4">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend(input)}
            disabled={isStreaming}
            placeholder="Type your reply..."
            className="flex-1 rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm text-white placeholder-slate-400 focus:border-indigo-300/60 focus:outline-none focus:ring-2 focus:ring-indigo-400/30 disabled:opacity-60"
          />
          <button
            onClick={() => handleSend(input)}
            disabled={isStreaming || !input.trim()}
            className="rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:brightness-110 disabled:opacity-40"
          >
            Send
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 border-t border-white/10 bg-black/10 px-6 py-4">
          <button
            onClick={onDeletePost}
            className="flex-1 rounded-xl bg-teal-500 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-teal-400"
          >
            Delete Post
          </button>
          <button
            onClick={onPublishAnyway}
            className="flex-1 rounded-xl border border-amber-300/30 bg-amber-300/10 py-3 text-sm font-semibold text-amber-200 transition hover:bg-amber-300/20"
          >
            Publish Anyway
          </button>
        </div>
      </div>
    </div>
  );
}
