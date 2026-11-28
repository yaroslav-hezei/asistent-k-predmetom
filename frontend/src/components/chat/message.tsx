"use client";

import { TriangleAlert, UserRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { BrandMark } from "@/components/account-marks";
import { Button } from "@/components/ui/button";
import type { ChatMessage } from "@/lib/api/client";
import { SourceCard } from "./source-card";

export function Message({ message }: { message: ChatMessage }) {
  const t = useTranslations("chat");
  const [highlight, setHighlight] = useState<number>();
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);

  const sourceId = (n: number) => "source-" + message.id + "-" + n;

  function reveal(n: number) {
    const target = document.getElementById(sourceId(n));
    target?.focus({ preventScroll: true });
    target?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "nearest" });
    setHighlight(n);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setHighlight(undefined), 1800);
  }

  if (message.role === "user") {
    return <p className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap wrap-anywhere rounded-2xl bg-fei-soft px-4 py-3">{message.text}</p>;
  }

  const sources = message.sources.toSorted((a, b) => a.n - b.n);
  const outdated = sources.some(source => source.type === "sheet" && source.outdated);
  const unverified = sources.find(source => source.type === "answer" && !source.verified);

  return (
    <article className="flex gap-2.5 md:gap-3">
      <BrandMark />
      <div className="min-w-0 flex-1">
        {message.found === false ? (
          <>
            <p><strong>{t("unknown")}</strong> {t("unknownDetail")}</p>
            <div className="mt-3 rounded-xl border border-line bg-card p-4">
              <h2 className="font-semibold">{t("askOthers")}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{t("askOthersDetail")}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button disabled className="min-h-11 whitespace-normal">{t("publish")}</Button>
                <Button disabled variant="outline" className="min-h-11 whitespace-normal">{t("edit")}</Button>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">{t("publishingSoon")}</p>
            </div>
          </>
        ) : (
          <>
            <p className="whitespace-pre-wrap wrap-anywhere">
              {(message.text ?? "").split(/(\[\d+\])/g).map((part, index) => {
                const n = Number(part.slice(1, -1));
                return index % 2 === 1 && sources.some(source => source.n === n)
                  ? <button key={index} type="button" aria-label={t("reference", { n })} onClick={() => reveal(n)}
                      className="mx-0.5 inline rounded-md bg-fei-soft px-1.5 py-0.5 text-xs font-semibold text-fei-dark hover:underline">{part}</button>
                  : part;
              })}
            </p>
            {outdated && (
              <p className="mt-3 flex gap-2 rounded-lg border border-warn-border bg-warn-bg p-3 text-sm text-warn-text">
                <TriangleAlert size={18} aria-hidden="true" className="shrink-0" />{t("outdated")}
              </p>
            )}
            {unverified && (
              <p className="mt-3 flex gap-2 rounded-lg bg-unverified-bg p-3 text-sm text-unverified-text">
                <UserRound size={18} aria-hidden="true" className="shrink-0" />
                {t(unverified.author.kind === "vyucujuci" ? "unverifiedTeacherDetail" : "unverifiedDetail")}
              </p>
            )}
            {sources.length > 0 && (
              <section className="mt-4" aria-labelledby={"sources-" + message.id}>
                <h2 id={"sources-" + message.id} className="mb-2 text-sm font-semibold">{t("sources")}</h2>
                <ol className="space-y-2">
                  {sources.map(source => <SourceCard key={source.n} source={source} id={sourceId(source.n)} highlighted={highlight === source.n} />)}
                </ol>
              </section>
            )}
          </>
        )}
      </div>
    </article>
  );
}
