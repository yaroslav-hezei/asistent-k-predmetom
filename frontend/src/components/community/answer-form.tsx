"use client";

import { TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";

const ANSWER_MAX = 4000; // the API's limit

type Failure = "failed" | "login" | "own" | "gone";

/**
 * The answer form of a question. The answer goes into the assistant's knowledge base at once:
 * unverified, or verified when a teacher of the course writes it.
 */
export function AnswerForm({ questionId, verified, afterSend, onClose }: {
  questionId: string;
  /** The user teaches the course: the answer is verified from the start. */
  verified: boolean;
  /** "detail": stay and reload the page; "list": open the question with the new answer. */
  afterSend: "detail" | "list";
  /** "Zrušiť", and after the answer is shown. */
  onClose: () => void;
}) {
  const t = useTranslations("questions");
  const router = useRouter();
  const id = useId();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  // stays true until the page with the new answer is shown (a second or two)
  const [showing, startTransition] = useTransition();
  const [failure, setFailure] = useState<Failure>();
  const pending = sending || showing;
  const trimmed = text.trim();

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!trimmed || pending) return;
    setSending(true);
    setFailure(undefined);
    try {
      const { response } = await api.POST("/questions/{question_id}/answers", {
        params: { path: { question_id: questionId } },
        body: { text: trimmed },
      });
      if (response.ok) {
        startTransition(() => {
          if (afterSend === "list") router.push(`/questions/${questionId}`);
          else router.refresh();
          setText("");
          onClose();
        });
        return;
      }
      setFailure(response.status === 401 ? "login" : response.status === 403 ? "own"
        : response.status === 404 ? "gone" : "failed");
    } catch {
      setFailure("failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={send} className="mt-4 grid gap-3">
      <label htmlFor={id} className="sr-only">{t("answerLabel")}</label>
      <Textarea id={id} value={text} maxLength={ANSWER_MAX} autoFocus readOnly={pending}
        placeholder={t("answerPlaceholder")} onChange={(event) => setText(event.target.value)}
        className="min-h-[110px] rounded-xl border-line-strong bg-white px-4 py-3 text-[16px] leading-relaxed md:text-[16px]" />
      {failure && (
        <p role="alert" className="text-sm text-destructive">
          {t(`errors.${failure}`)}
          {failure === "login" && (
            <> <Link href="/login" className="font-semibold underline">{t("signIn")}</Link></>
          )}
        </p>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <p className="flex flex-1 gap-2 text-sm text-muted-foreground">
          <TriangleAlert size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <span>{t.rich(verified ? "answerHintTeacher" : "answerHint", {
            b: (chunks) => <strong className="font-semibold text-foreground">{chunks}</strong>,
          })}</span>
        </p>
        <div className="flex shrink-0 gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={pending}
            className="h-11 px-4 text-[15px]">
            {t("cancel")}
          </Button>
          <Button type="submit" disabled={!trimmed || pending}
            className="h-11 flex-1 px-5 text-[15px] font-semibold sm:flex-none">
            {pending ? t("sending") : t("send")}
          </Button>
        </div>
      </div>
    </form>
  );
}
