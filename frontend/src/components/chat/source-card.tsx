"use client";

import { ExternalLink, FileText, Megaphone, Users } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import type { Source } from "@/lib/api/client";

export function SourceCard({ source, id, highlighted }: { source: Source; id: string; highlighted: boolean }) {
  const t = useTranslations("chat");
  const locale = useLocale();
  const quote = useRef<HTMLQuoteElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [long, setLong] = useState(false);
  const sheet = source.type === "sheet";
  const Icon = sheet ? FileText : source.type === "answer" ? Users : Megaphone;
  const badge = sheet ? "official" : source.verified ? "verified" : "unverified";
  const badgeStyle = sheet ? "bg-official-bg text-official-text" : source.verified ? "bg-ok-bg text-ok-text" : "bg-unverified-bg text-unverified-text";
  const title = sheet ? "sheet" : source.type === "course_note" ? "courseNote" : source.author.kind === "vyucujuci" ? "teacherAnswer" : "studentAnswer";
  const date = new Date(source.date);
  const formattedDate = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    ...(source.type === "answer" ? { timeStyle: "short" } : { timeZone: "Europe/Bratislava" }),
  }).format(date);

  useEffect(() => {
    const element = quote.current;
    if (!element || expanded) return;
    const measure = () => setLong(element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [expanded, source.quote]);

  return (
    <li id={id} tabIndex={-1} className={`scroll-m-3 rounded-xl border border-line bg-card p-3 transition-shadow ${highlighted ? "ring-2 ring-fei" : ""}`}>
      <div className="flex flex-wrap items-start gap-x-2 gap-y-1">
        <span className="rounded-md bg-fei-soft px-2 py-1 text-xs font-semibold text-fei-dark">{source.n}</span>
        <Icon size={18} className="mt-0.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div className="min-w-0 flex-[1_1_12rem] break-words">
          <p className="font-semibold">{t(title)}</p>
          <p className="text-sm text-muted-foreground">
            {sheet ? [source.section, t("asOf", { date: formattedDate })].filter(Boolean).join(" · ")
              : [source.author.nickname ?? t(source.author.kind === "vyucujuci" ? "teacher" : "student"), formattedDate].join(" · ")}
          </p>
          {source.type === "answer" && source.question && (
            <p className="truncate text-sm text-muted-foreground" title={source.question.text}>
              {t("onQuestion", { question: source.question.text })}
            </p>
          )}
        </div>
        <span className={`rounded-full px-2 py-1 text-xs font-medium ${badgeStyle}`}>{t(badge)}</span>
        {sheet && source.url && (
          <a href={source.url} target="_blank" rel="noopener noreferrer" aria-label={t("openMais")}
            className="grid size-11 shrink-0 place-items-center rounded-lg text-fei-dark hover:bg-fei-soft">
            <ExternalLink size={17} aria-hidden="true" />
          </a>
        )}
      </div>
      <blockquote ref={quote} id={id + "-quote"}
        className={`mt-2 whitespace-pre-wrap [overflow-wrap:anywhere] border-l-2 border-line-strong pl-3 text-sm leading-6 ${expanded ? "" : "line-clamp-4"}`}>
        {source.quote}
      </blockquote>
      {(long || expanded) && (
        <button type="button" aria-expanded={expanded} aria-controls={id + "-quote"} onClick={() => setExpanded(!expanded)}
          className="min-h-11 rounded-lg text-sm font-semibold text-fei-dark hover:underline">
          {t(expanded ? "hideQuote" : "showQuote")}
        </button>
      )}
    </li>
  );
}
