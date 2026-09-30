"use client";

import { useRef, useState } from "react";
import {
  createTranslator,
  NextIntlClientProvider,
  useLocale,
  useTranslations,
} from "next-intl";
import { DUMMY_POSTS, MainFeed } from "@/components/MainFeed";
import { InterventionModal } from "@/components/InterventionModal";
import { DEFAULT_LANGUAGE, dirOf, isLanguage } from "@/i18n/config";
import { MESSAGES } from "@/i18n/messages";
import { classifyPost, streamChat } from "@/lib/api";
import type { Branch, Language, Message, Post, Verdict } from "@/lib/types";

/* ==========================================================================
   COMPONENT 3: App (Controller)
   Owns the state. Post click -> /api/classify -> publish, or open the modal
   and stream the supportive chat from /api/chat.
   ========================================================================== */

// There is no login yet, so the person's name is fixed here and sent to the chat.
const USER_NAME = "Mark";

export default function Page() {
  const t = useTranslations();
  // The language picked in the UI; the chat replies in it too.
  const locale = useLocale();
  const language: Language = isLanguage(locale) ? locale : DEFAULT_LANGUAGE;
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
  // Set once the server sends the closing message; the modal then shows the option buttons.
  const [menuBranch, setMenuBranch] = useState<Branch | null>(null);
  // The chat panel speaks the post's language; the picker only decides when it is unknown.
  const modalLanguage: Language = pendingVerdict?.language ?? language;

  const abortRef = useRef<AbortController | null>(null);
  const nextId = useRef(0);

  const publish = (text: string) => {
    setPosts((prev) => [
      {
        id: Date.now(),
        author: t("feed.you"),
        handle: "@you",
        time: t("feed.now"),
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
      const { menu } = await streamChat(
        post,
        verdict,
        history,
        USER_NAME,
        language,
        (delta) =>
          setMessages((prev) =>
            prev.map((m) => (m.id === aiId ? { ...m, text: m.text + delta } : m)),
          ),
        controller.signal,
      );
      if (menu) setMenuBranch(menu);
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error("chat failed:", err instanceof Error ? err.message : err);
      // The user can still delete or publish, so a chat failure never blocks them.
      setMessages((prev) => prev.filter((m) => !(m.id === aiId && m.text === "")));
      // Built outside the modal's provider, so it needs the post's language explicitly.
      const postLanguage = verdict.language ?? language;
      const tErrors = createTranslator({
        locale: postLanguage,
        messages: MESSAGES[postLanguage],
        namespace: "errors",
      });
      setChatError(tErrors("chat"));
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
      setError(t("errors.classify"));
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
    setMenuBranch(null);
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
      <div lang={modalLanguage} dir={dirOf(modalLanguage)}>
        <NextIntlClientProvider locale={modalLanguage} messages={MESSAGES[modalLanguage]}>
          <InterventionModal
            isOpen={isModalOpen}
            messages={messages}
            isStreaming={isStreaming}
            chatError={chatError}
            menuBranch={menuBranch}
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
        </NextIntlClientProvider>
      </div>
    </>
  );
}
