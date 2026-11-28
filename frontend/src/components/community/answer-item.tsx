"use client";

import { BadgeCheck, Heart } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import type { CommunityAnswer } from "@/lib/api/community";
import { api } from "@/lib/api/client";
import { AuthorLine } from "./author-line";
import { HideButton } from "./hide-button";

/** An answer on a question's page: author, Overené / Neoverené, "Poďakovať". */
export function AnswerItem({ answer, teaches }: { answer: CommunityAnswer; teaches: boolean }) {
  const t = useTranslations("questions");
  const [thanks, setThanks] = useState({ count: answer.thanks, mine: answer.thanked_by_me });
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function thank() {
    setPending(true);
    setFailed(false);
    try {
      const { data } = await api.POST("/answers/{answer_id}/thanks", {
        params: { path: { answer_id: answer.id } },
      });
      if (data) setThanks({ count: data.thanks, mine: data.thanked_by_me });
      else setFailed(true);
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <li className="rounded-xl border border-line bg-card px-4 py-3.5 sm:px-5">
      <p className="whitespace-pre-line break-words leading-relaxed">{answer.text}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
        <span><AuthorLine author={answer.author} createdAt={answer.created_at} /></span>
        {answer.verified ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-ok-bg px-2.5 py-0.5 text-[13px] font-semibold text-ok-text">
            <BadgeCheck size={14} aria-hidden="true" />
            {t("verified")}
          </span>
        ) : (
          <span className="rounded-full bg-unverified-bg px-2.5 py-0.5 text-[13px] font-semibold text-unverified-text">
            {t("unverified")}
          </span>
        )}
        <span className="ml-auto flex items-center gap-1">
          {answer.mine ? (
            thanks.count > 0 && <span className="py-2">{t("thanks", { count: thanks.count })}</span>
          ) : (
            <button type="button" onClick={thank} disabled={pending || thanks.mine} aria-pressed={thanks.mine}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2 font-medium text-foreground hover:bg-nav-active disabled:cursor-default disabled:hover:bg-transparent md:min-h-9">
              <Heart size={15} aria-hidden="true" className={thanks.mine ? "fill-fei text-fei" : ""} />
              {t(thanks.mine ? "thanked" : "thank")}
              {thanks.count > 0 && <span className="text-muted-foreground">· {thanks.count}</span>}
            </button>
          )}
          {teaches && <HideButton kind="answer" id={answer.id} />}
        </span>
      </div>
      {!answer.verified && (
        <p className="mt-1.5 text-[13px] text-muted-foreground">{t("unverifiedHint")}</p>
      )}
      {failed && <p role="alert" className="mt-1.5 text-sm text-destructive">{t("errors.action")}</p>}
    </li>
  );
}
