"use client";

import { useEffect, useRef, useState } from "react";
import type { Message } from "@/lib/types";

/* ==========================================================================
   COMPONENT 2: InterventionModal
   Overlay chat. Presentational: the parent owns the conversation.
     - `isOpen`          -> controlled by parent
     - `messages`        -> the conversation so far (assistant text streams in)
     - `isStreaming`     -> true while a reply is arriving; input is disabled
     - `chatError`       -> shown under the chat if a reply failed
     - `onSendMessage`   -> called with the user's reply text
     - `onDeletePost`, `onPublishAnyway` -> button handlers
     - `onClose` -> exit without deleting or publishing (back to editing)
   ========================================================================== */

type InterventionModalProps = {
  isOpen?: boolean;
  messages?: Message[];
  isStreaming?: boolean;
  chatError?: string | null;
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
  onSendMessage = () => {},
  onDeletePost = () => {},
  onPublishAnyway = () => {},
  onClose = () => {},
}: InterventionModalProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, chatError]);

  if (!isOpen) return null;

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput("");
    onSendMessage(text);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="flex h-[36rem] max-h-full w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <span className="font-semibold text-slate-800">Before you post</span>
          <button
            onClick={onClose}
            aria-label="Close and keep editing my post"
            className="flex h-8 w-8 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-300"
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
        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-5 py-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-white text-slate-700 shadow-sm ring-1 ring-slate-200"
                }`}
              >
                {m.text || (isStreaming && m.role === "ai" ? "…" : "")}
              </div>
            </div>
          ))}
          {chatError && (
            <p role="alert" className="text-sm text-rose-600">
              {chatError}
            </p>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Chat input */}
        <div className="flex gap-2 border-t border-slate-200 px-4 py-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            disabled={isStreaming}
            placeholder="Type your reply..."
            className="flex-1 rounded-full border border-slate-200 px-4 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 disabled:bg-slate-50"
          />
          <button
            onClick={handleSend}
            disabled={isStreaming}
            className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-900 disabled:opacity-50"
          >
            Send
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 border-t border-slate-200 px-4 py-4">
          <button
            onClick={onDeletePost}
            className="flex-1 rounded-lg bg-teal-600 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-700"
          >
            Delete Post
          </button>
          <button
            onClick={onPublishAnyway}
            className="flex-1 rounded-lg border border-amber-300 bg-amber-50 py-2.5 text-sm font-semibold text-amber-800 transition hover:bg-amber-100"
          >
            Publish Anyway
          </button>
        </div>
      </div>
    </div>
  );
}
