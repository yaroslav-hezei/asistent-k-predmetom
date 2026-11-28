"use client";

import { BadgeCheck, Heart, MessageSquare } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useState } from "react";
import { RelativeTime } from "@/components/community/relative-time";
import { api } from "@/lib/api/client";
import type { Notification } from "@/lib/api/community";

const button = "inline-flex min-h-11 items-center gap-1.5 rounded-[10px] px-4 font-semibold";

/** "Na tvoju otázku niekto odpovedal": the question, the answer and what to do next. */
export function NotificationCard({ notification, unread, thanked, onThanked }: {
  notification: Notification;
  /** Unread when the page was opened (stays highlighted while the page is open). */
  unread: boolean;
  /** Kept by the list, so it survives switching the tabs. */
  thanked: boolean;
  onThanked: (answerId: string) => void;
}) {
  const t = useTranslations("notifications");
  const questions = useTranslations("questions");
  const { question, answer } = notification;
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function thank() {
    if (!answer) return;
    setPending(true);
    setFailed(false);
    try {
      const { data } = await api.POST("/answers/{answer_id}/thanks", {
        params: { path: { answer_id: answer.id } },
      });
      if (data?.thanked_by_me) onThanked(answer.id);
      else setFailed(true);
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <article className={`relative flex gap-3 rounded-[14px] border px-4 py-4 sm:gap-4 sm:px-6 sm:py-5 ${unread ? "border-fei/60 bg-fei-soft/40" : "border-line bg-card"}`}>
      <span aria-hidden="true" className={`grid size-9 shrink-0 place-items-center rounded-[10px] text-fei-dark ${unread ? "bg-fei-soft" : "bg-sidebar"}`}>
        <MessageSquare size={18} />
      </span>
      <div className="min-w-0 flex-1">
        <h2 className="pr-5 font-semibold leading-snug">
          {t(answer?.author.kind === "vyucujuci" ? "answeredByTeacher" : "answered")}
          {unread && <span className="sr-only"> ({t("unreadLabel")})</span>}
        </h2>
        <p className="mt-1 break-words italic text-foreground/80">{t("quote", { text: question.text })}</p>
        {answer ? (
          <div className="mt-3 rounded-xl bg-sidebar px-4 py-3">
            <p className="break-words">
              <span className="font-semibold">{answer.author.nickname}: </span>
              <span className="whitespace-pre-line">{answer.text}</span>
            </p>
            <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-muted-foreground">
              {answer.verified ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-ok-bg px-2.5 py-0.5 font-semibold text-ok-text">
                  <BadgeCheck size={14} aria-hidden="true" />
                  {questions("verified")}
                </span>
              ) : (
                <>
                  <span className="rounded-full bg-unverified-bg px-2.5 py-0.5 font-semibold text-unverified-text">
                    {questions("unverified")}
                  </span>
                  <span>{questions("unverifiedHint")}</span>
                </>
              )}
            </p>
          </div>
        ) : (
          <p className="mt-3 text-muted-foreground">{t("answerGone")}</p>
        )}
        <p className="mt-2 text-sm text-muted-foreground">
          {question.course.name}
          <span aria-hidden="true"> · </span>
          <RelativeTime value={notification.created_at} />
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {notification.chat_id && (
            <Link href={`/chat/${notification.chat_id}`} className={`${button} bg-fei text-on-fei hover:bg-fei/80`}>
              {t("showInChat")}
            </Link>
          )}
          <Link href={`/questions/${question.id}`}
            className={`${button} ${notification.chat_id ? "border border-line-strong bg-card hover:bg-sidebar" : "bg-fei text-on-fei hover:bg-fei/80"}`}>
            {t("showQuestion")}
          </Link>
          {answer && (
            <button type="button" onClick={thank} disabled={pending || thanked} aria-pressed={thanked}
              className={`${button} border border-line-strong bg-card font-medium hover:bg-sidebar disabled:cursor-default disabled:hover:bg-card`}>
              <Heart size={15} aria-hidden="true" className={thanked ? "fill-fei text-fei" : ""} />
              {questions(thanked ? "thanked" : "thank")}
            </button>
          )}
        </div>
        {failed && <p role="alert" className="mt-2 text-sm text-destructive">{questions("errors.action")}</p>}
      </div>
      {unread && <span aria-hidden="true" className="absolute top-5 right-5 size-2.5 rounded-full bg-fei" />}
    </article>
  );
}
