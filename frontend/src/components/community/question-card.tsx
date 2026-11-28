"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useState } from "react";
import type { QuestionSummary } from "@/lib/api/community";
import { AnswerForm } from "./answer-form";
import { AuthorLine } from "./author-line";
import { HideButton } from "./hide-button";
import { useIsRecent } from "./relative-time";

/**
 * A question of "Otázky komunity". In a list the text links to the question's page; open
 * questions get the "Odpovedať" form right in the list (screen 04).
 */
export function QuestionCard({ question, variant, showCourse, teaches }: {
  question: QuestionSummary;
  /** "list": a card in a tab; "detail": the head of the question's own page. */
  variant: "list" | "detail";
  /** Show the course name (the list of all my courses). */
  showCourse: boolean;
  /** The user teaches the course: answers verified, may hide the question. */
  teaches: boolean;
}) {
  const t = useTranslations("questions");
  const [answering, setAnswering] = useState(false);
  const recent = useIsRecent(question.created_at);
  const href = `/questions/${question.id}`;
  const Heading = variant === "detail" ? "h1" : "h2";
  const isNew = question.status === "open" && recent;

  return (
    <article className="rounded-[14px] border border-line bg-card px-4 py-4 sm:px-6 sm:py-5">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          {showCourse && (
            <p className="mb-1 text-[13px] font-medium text-fei-dark">{question.course.name}</p>
          )}
          <Heading className={`font-semibold leading-snug break-words ${variant === "detail" ? "text-xl" : "text-[17px]"}`}>
            {variant === "list" ? <Link href={href} className="hover:underline">{question.text}</Link> : question.text}
          </Heading>
          <p className="mt-1 text-sm text-muted-foreground">
            <AuthorLine author={question.author} createdAt={question.created_at} />
            <span aria-hidden="true"> · </span>
            {t("answers", { count: question.answer_count })}
            {question.from_assistant && (
              <><span aria-hidden="true"> · </span>{t("fromAssistant")}</>
            )}
          </p>
        </div>
        {isNew && (
          <span className="shrink-0 rounded-full bg-fei-soft px-2.5 py-0.5 text-[13px] font-semibold text-fei-dark">
            {t("new")}
          </span>
        )}
      </div>

      {answering ? (
        <AnswerForm questionId={question.id} verified={teaches} afterSend={variant}
          onClose={() => setAnswering(false)} />
      ) : (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 -mb-1">
          {question.mine ? (
            <span className="py-2.5 text-sm text-muted-foreground">{t("mine")}</span>
          ) : (
            <button type="button" onClick={() => setAnswering(true)}
              className="min-h-11 font-semibold text-fei-dark hover:underline">
              {t("answer")}
            </button>
          )}
          {variant === "list" && question.answer_count > 0 && (
            <Link href={href} className="inline-flex min-h-11 items-center font-semibold text-fei-dark hover:underline">
              {t("showAnswers")}
            </Link>
          )}
          {teaches && (
            <span className="ml-auto">
              <HideButton kind="question" id={question.id}
                afterHide={variant === "detail" ? `/questions?course=${question.course.id}` : undefined} />
            </span>
          )}
        </div>
      )}
    </article>
  );
}
