"use client";

import { useRef, useState } from "react";
import { DUMMY_POSTS, MainFeed } from "@/components/MainFeed";
import { InterventionModal } from "@/components/InterventionModal";
import { classifyPost, streamChat } from "@/lib/api";
import type { Message, Post, Verdict } from "@/lib/types";

/* ==========================================================================
   COMPONENT 3: App (Controller)
   Owns the state. Post click -> /api/classify -> publish, or open the modal
   and stream the supportive chat from /api/chat.
   ========================================================================== */

export default function Page() {
  const [posts, setPosts] = useState<Post[]>(DUMMY_POSTS);
  const [draft, setDraft] = useState("");
  const [isPosting, setIsPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pendingPost, setPendingPost] = useState("");
  const [pendingVerdict, setPendingVerdict] = useState<Verdict | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const nextId = useRef(0);

  const publish = (text: string) => {
    setPosts((prev) => [
      {
        id: Date.now(),
        author: "You",
        handle: "@you",
        time: "now",
        text,
        colorClass: "bg-slate-900 text-white",
      },
      ...prev,
    ]);
    setDraft("");
  };

  // Streams one assistant reply. `history` is everything before that reply;
  // an empty history asks the server for the opening message.
  const runAssistantTurn = async (
    post: string,
    verdict: Verdict,
    history: Message[],
  ) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const aiId = nextId.current++;
    setMessages([...history, { id: aiId, role: "ai", text: "" }]);
    setIsStreaming(true);
    setChatError(null);

    try {
      await streamChat(
        post,
        verdict,
        history,
        (delta) =>
          setMessages((prev) =>
            prev.map((m) => (m.id === aiId ? { ...m, text: m.text + delta } : m)),
          ),
        controller.signal,
      );
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error("chat failed:", err instanceof Error ? err.message : err);
      // The user can still delete or publish, so a chat failure never blocks them.
      setMessages((prev) => prev.filter((m) => !(m.id === aiId && m.text === "")));
      setChatError(
        "Something went wrong. You can try sending again, or choose an option below.",
      );
    } finally {
      if (abortRef.current === controller) setIsStreaming(false);
    }
  };

  const handlePostClick = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    setIsPosting(true);
    setError(null);
    try {
      const verdict = await classifyPost(trimmed);
      if (verdict.harmful) {
        setPendingPost(trimmed);
        setPendingVerdict(verdict);
        setIsModalOpen(true);
        void runAssistantTurn(trimmed, verdict, []);
      } else {
        publish(trimmed);
      }
    } catch (err) {
      console.error("classify failed:", err instanceof Error ? err.message : err);
      // Fail closed: never publish a post that could not be checked.
      setError("We couldn't check your post. Please try again.");
    } finally {
      setIsPosting(false);
    }
  };

  const handleSendMessage = (text: string) => {
    if (isStreaming || !pendingVerdict) return;
    const userMessage: Message = { id: nextId.current++, role: "user", text };
    void runAssistantTurn(pendingPost, pendingVerdict, [...messages, userMessage]);
  };

  const closeModal = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setMessages([]);
    setChatError(null);
    setIsModalOpen(false);
    setPendingPost("");
    setPendingVerdict(null);
  };

  return (
    <>
      <MainFeed
        posts={posts}
        draft={draft}
        onDraftChange={setDraft}
        onPostClick={handlePostClick}
        isPosting={isPosting}
        error={error}
      />
      <InterventionModal
        isOpen={isModalOpen}
        messages={messages}
        isStreaming={isStreaming}
        chatError={chatError}
        onSendMessage={handleSendMessage}
        onDeletePost={() => {
          setDraft("");
          closeModal();
        }}
        onPublishAnyway={() => {
          publish(pendingPost);
          closeModal();
        }}
        onClose={closeModal} // back to editing; draft stays in the feed
      />
    </>
  );
}
