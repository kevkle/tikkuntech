"use client";

import { useState } from "react";
import type { Message } from "@/lib/types";

/* ==========================================================================
   COMPONENT 2: InterventionModal
   Overlay chat. Backend hookup points:
     - `isOpen`          -> controlled by parent
     - `initialMessage`  -> first AI message (can come from server)
     - `onSendMessage`   -> called with the user's reply text
     - `onDeletePost`, `onPublishAnyway`, `onClose` -> button handlers
   The two bottom buttons are static for now (no-op defaults).
   ========================================================================== */

const INITIAL_AI_MESSAGE =
  "Hey, I noticed the content of your post. I'm genuinely interested to hear what led you to write this. Care to share?";

type InterventionModalProps = {
  isOpen?: boolean;
  initialMessage?: string;
  onSendMessage?: (text: string) => void;
  onDeletePost?: () => void;
  onPublishAnyway?: () => void;
};

export function InterventionModal({
  isOpen = false,
  initialMessage = INITIAL_AI_MESSAGE,
  onSendMessage = () => {},
  onDeletePost = () => {},
  onPublishAnyway = () => {},
}: InterventionModalProps) {
  const [messages, setMessages] = useState<Message[]>([
    { id: 0, role: "ai", text: initialMessage },
  ]);
  const [input, setInput] = useState("");

  if (!isOpen) return null;

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    setMessages((prev) => [...prev, { id: prev.length, role: "user", text }]);
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
        <div className="border-b border-slate-200 px-5 py-4 font-semibold text-slate-800">
          Before you post
        </div>

        {/* Chat window */}
        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-5 py-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-white text-slate-700 shadow-sm ring-1 ring-slate-200"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
        </div>

        {/* Chat input */}
        <div className="flex gap-2 border-t border-slate-200 px-4 py-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Type your reply..."
            className="flex-1 rounded-full border border-slate-200 px-4 py-2 text-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
          <button
            onClick={handleSend}
            className="rounded-full bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-900"
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
