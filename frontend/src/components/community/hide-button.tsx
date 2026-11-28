"use client";

import { EyeOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api/client";

/** A teacher of the course hides spam: a question (with its answers) or one answer. */
export function HideButton({ kind, id, afterHide }: {
  kind: "question" | "answer";
  id: string;
  /** Where to go after hiding; the current page is reloaded when not set. */
  afterHide?: string;
}) {
  const t = useTranslations("questions");
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function hide() {
    if (!window.confirm(t(kind === "question" ? "hideQuestionConfirm" : "hideAnswerConfirm"))) return;
    setPending(true);
    setFailed(false);
    try {
      const { response } = kind === "question"
        ? await api.POST("/questions/{question_id}/hide", { params: { path: { question_id: id } } })
        : await api.POST("/answers/{answer_id}/hide", { params: { path: { answer_id: id } } });
      // 404: already hidden by someone else — the result is the same
      if (response.ok || response.status === 404) {
        if (afterHide) router.push(afterHide);
        else router.refresh();
        return;
      }
      setFailed(true);
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <button type="button" onClick={hide} disabled={pending}
        className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2 text-sm font-medium text-warn-text hover:bg-warn-bg disabled:opacity-50 md:min-h-9">
        <EyeOff size={15} aria-hidden="true" />
        {t(kind === "question" ? "hideQuestion" : "hideAnswer")}
      </button>
      {failed && <span role="alert" className="text-sm text-destructive">{t("errors.action")}</span>}
    </span>
  );
}
