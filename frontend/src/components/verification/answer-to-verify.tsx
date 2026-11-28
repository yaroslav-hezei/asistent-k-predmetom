"use client";

import { Check, MessageSquarePlus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { AnswerForm } from "@/components/community/answer-form";
import { AuthorLine } from "@/components/community/author-line";
import { api } from "@/lib/api/client";
import type { AnswerToVerify as Answer } from "@/lib/api/teacher";

const button = "inline-flex min-h-11 items-center justify-center gap-1.5 rounded-[10px] px-4 font-semibold disabled:opacity-50";

/**
 * A student's answer waiting for the teacher (change 3 after the test: the teacher never edits it):
 * "Overiť", "Pridať odpoveď" (the teacher's own verified answer) or "Zmazať" (hide as spam).
 */
export function AnswerToVerify({ answer }: { answer: Answer }) {
  const t = useTranslations("verification");
  const questions = useTranslations("questions");
  const router = useRouter();
  const [answering, setAnswering] = useState(false);
  const [sending, setSending] = useState(false);
  const [showing, startTransition] = useTransition();
  const [failed, setFailed] = useState(false);
  const pending = sending || showing;

  async function act(action: "verify" | "hide") {
    if (action === "hide" && !window.confirm(questions("hideAnswerConfirm"))) return;
    setSending(true);
    setFailed(false);
    try {
      const path = { params: { path: { answer_id: answer.id } } };
      const { response } = action === "verify"
        ? await api.POST("/answers/{answer_id}/verify", path)
        : await api.POST("/answers/{answer_id}/hide", path);
      // 404: hidden meanwhile (by another teacher) — it leaves the list either way
      if (response.ok || response.status === 404) startTransition(() => router.refresh());
      else setFailed(true);
    } catch {
      setFailed(true);
    } finally {
      setSending(false);
    }
  }

  return (
    <article className="rounded-[14px] border border-line bg-card px-4 py-4 sm:px-6 sm:py-5">
      <h3 className="text-[17px] font-semibold leading-snug break-words">
        <Link href={`/questions/${answer.question.id}`} className="hover:underline">{answer.question.text}</Link>
      </h3>
      <p className="mt-3 whitespace-pre-line break-words rounded-xl bg-sidebar px-4 py-3 leading-relaxed">
        {answer.text}
      </p>
      {answering ? (
        <AnswerForm questionId={answer.question.id} verified afterSend="detail"
          onClose={() => setAnswering(false)} />
      ) : (
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
          <p className="flex flex-1 flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
            <span><AuthorLine author={answer.author} createdAt={answer.created_at} /></span>
            <span className="rounded-full bg-unverified-bg px-2.5 py-0.5 text-[13px] font-semibold text-unverified-text">
              {questions("unverified")}
            </span>
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={pending} onClick={() => act("verify")}
              className={`${button} bg-ok-text text-white hover:bg-ok-text/90`}>
              <Check size={16} aria-hidden="true" />
              {t("verify")}
            </button>
            <button type="button" disabled={pending} onClick={() => setAnswering(true)}
              className={`${button} border border-line-strong bg-card font-medium hover:bg-sidebar`}>
              <MessageSquarePlus size={16} aria-hidden="true" />
              {t("addAnswer")}
            </button>
            <button type="button" disabled={pending} onClick={() => act("hide")}
              className={`${button} border border-line-strong bg-card font-medium text-warn-text hover:bg-warn-bg`}>
              <Trash2 size={16} aria-hidden="true" />
              {t("delete")}
            </button>
          </div>
        </div>
      )}
      {failed && <p role="alert" className="mt-2 text-sm text-destructive">{questions("errors.action")}</p>}
    </article>
  );
}
