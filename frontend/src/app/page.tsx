"use client";

import { useState } from "react";
import { MainFeed } from "@/components/MainFeed";
import { InterventionModal } from "@/components/InterventionModal";

/* ==========================================================================
   COMPONENT 3: App (Controller)
   Owns the state. This is where server logic should be wired in.
   ========================================================================== */

export default function Page() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pendingPost, setPendingPost] = useState("");

  const handlePostClick = (text: string) => {
    setPendingPost(text); // TODO (backend): send `text` to moderation/AI endpoint
    setIsModalOpen(true);
  };

  return (
    <>
      <MainFeed onPostClick={handlePostClick} />
      <InterventionModal
        isOpen={isModalOpen}
        onSendMessage={() => {
          /* TODO (backend): send reply, append AI response */
        }}
        onDeletePost={() => setIsModalOpen(false)} // TODO: discard draft
        onPublishAnyway={() => setIsModalOpen(false)} // TODO: publish `pendingPost`
      />
    </>
  );
}
