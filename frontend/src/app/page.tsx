"use client";

import { useState } from "react";
import { DUMMY_POSTS, MainFeed } from "@/components/MainFeed";
import { InterventionModal } from "@/components/InterventionModal";
import { classifyPost } from "@/lib/api";
import type { Post } from "@/lib/types";

/* ==========================================================================
   COMPONENT 3: App (Controller)
   Owns the state. Post click -> /api/classify -> publish, or open the modal.
   ========================================================================== */

export default function Page() {
  const [posts, setPosts] = useState<Post[]>(DUMMY_POSTS);
  const [draft, setDraft] = useState("");
  const [isPosting, setIsPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pendingPost, setPendingPost] = useState("");

  const publish = (text: string) => {
    setPosts((prev) => [
      { id: Date.now(), author: "You", handle: "@you", time: "now", text },
      ...prev,
    ]);
    setDraft("");
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
        setIsModalOpen(true);
      } else {
        publish(trimmed);
      }
    } catch {
      // Fail closed: never publish a post that could not be checked.
      setError("We couldn't check your post. Please try again.");
    } finally {
      setIsPosting(false);
    }
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setPendingPost("");
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
        onSendMessage={() => {
          /* TODO (Phase 3): send reply, append AI response */
        }}
        onDeletePost={() => {
          setDraft("");
          closeModal();
        }}
        onPublishAnyway={() => {
          publish(pendingPost);
          closeModal();
        }}
      />
    </>
  );
}
