"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { CourseHeader } from "@/components/course-header";
import { api, type ChatMessage, type Course } from "@/lib/api/client";
import { ChatNotice } from "./chat-notice";
import { Composer } from "./composer";
import { CourseTitle } from "./course-title";
import { Message } from "./message";

const emptyMessages: ChatMessage[] = [];
const subscribeToDraft = () => () => {};
const emptyDraft = () => "";

function readDraft(key: string) {
  try {
    return sessionStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

function writeDraft(key: string, draft: string) {
  try {
    if (draft) sessionStorage.setItem(key, draft);
    else sessionStorage.removeItem(key);
  } catch {
    // The draft remains visible on this page if storage is unavailable.
  }
}

export function ChatView({ course, pathname, chatId, initialMessages = emptyMessages, userId }: {
  course: Course;
  pathname: string;
  chatId?: string;
  initialMessages?: ChatMessage[];
  userId?: string;
}) {
  const t = useTranslations("chat");
  const router = useRouter();
  const [exchange, setExchange] = useState<ChatMessage[]>([]);
  const draftKey = "hip.chatDraft:" + userId + ":" + (chatId ?? course.id);
  const savedDraft = useSyncExternalStore(subscribeToDraft, () => userId ? readDraft(draftKey) : "", emptyDraft);
  const [editedValue, setValue] = useState<string>();
  const value = editedValue ?? savedDraft;
  const [pending, setPending] = useState("");
  const [error, setError] = useState(false);
  const [expired, setExpired] = useState(false);
  const section = useRef<HTMLElement>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const sending = useRef(false);
  const currentId = useRef(chatId);
  const savedIds = new Set(initialMessages.map(message => message.id));
  const messages = [...initialMessages, ...exchange.filter(message => !savedIds.has(message.id))];

  useLayoutEffect(() => {
    const area = scroll.current;
    if (area) area.scrollTop = area.scrollHeight;
  }, [initialMessages, exchange, pending]);

  useEffect(() => {
    const viewport = window.visualViewport;
    const container = section.current;
    if (!viewport || !container) return;
    const resize = () => {
      container.style.setProperty("--chat-viewport", viewport.height + "px");
      container.toggleAttribute("data-compact", viewport.height < 420);
      if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
    };
    resize();
    viewport.addEventListener("resize", resize);
    return () => viewport.removeEventListener("resize", resize);
  }, []);

  async function ask(question: string) {
    if (sending.current) return;
    sending.current = true;
    setPending(question);
    setError(false);
    try {
      const { response, data } = await api.POST("/ask", {
        body: { course_id: course.id, question, chat_id: currentId.current ?? null },
      });
      if (response.status === 401) {
        writeDraft(draftKey, value);
        setExpired(true);
        return;
      }
      if (!data) {
        setError(true);
        return;
      }
      const previousId = currentId.current;
      currentId.current = data.chat_id;
      setExchange(previous => [...previous, data.question, data.answer]);
      writeDraft(draftKey, "");
      setValue("");
      if (!previousId) router.replace("/chat/" + encodeURIComponent(data.chat_id), { scroll: false });
      router.refresh();
    } catch {
      setError(true);
    } finally {
      sending.current = false;
      setPending("");
    }
  }

  return (
    <section ref={section} className="group/chat mx-auto flex h-[calc(var(--chat-viewport,100dvh)-62px)] w-full max-w-[760px] flex-col">
      <CourseTitle pathname={pathname} name={course.name} />
      <div className="shrink-0 px-4 pt-2 group-data-compact/chat:hidden md:px-5"><CourseHeader course={course} /></div>
      {userId && !expired ? (
        <>
          <div ref={scroll} className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 md:px-5">
            {messages.length === 0 && !pending && <p className="text-muted-foreground">{t("hint", { course: course.name })}</p>}
            <div className="space-y-5">
              {messages.map(message => <Message key={message.id} message={message} />)}
              {pending && <>
                <p className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap wrap-anywhere rounded-2xl bg-fei-soft px-4 py-3">{pending}</p>
                <p role="status" className="text-sm text-muted-foreground">{t("waiting")}</p>
              </>}
            </div>
          </div>
          <Composer value={value} onChange={setValue} onSend={ask} busy={!!pending} error={error} />
        </>
      ) : <ChatNotice login draft={expired ? value : undefined} />}
    </section>
  );
}
