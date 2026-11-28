"use client";

import { Users } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Notice } from "@/components/community/notice";
import { api } from "@/lib/api/client";
import type { Notification } from "@/lib/api/community";
import { NotificationCard } from "./notification-card";

type Tab = "all" | "unread";

/**
 * "Upozornenia". Opening the page marks the shown notifications as read (the sidebar count goes
 * to 0); they stay highlighted as new, and in "Neprečítané", while the page is open.
 */
export function NotificationsView({ notifications, openQuestions }: {
  notifications: Notification[];
  /** Open questions of "Moje predmety" without the user's own (the community card). */
  openQuestions: number;
}) {
  const t = useTranslations("notifications");
  const [tab, setTab] = useState<Tab>("all");
  // what was unread when the page was opened
  const [unreadIds] = useState(() => new Set(notifications.filter((n) => !n.read).map((n) => n.id)));
  const [thanked, setThanked] = useState(() => new Set(
    notifications.flatMap((n) => (n.answer?.thanked_by_me ? [n.answer.id] : [])),
  ));

  useEffect(() => {
    if (unreadIds.size === 0) return;
    // Only these: a notification that arrives meanwhile stays unread. A failure changes nothing
    // visible; the next visit tries again.
    api.POST("/notifications/read", { body: { ids: [...unreadIds] } }).catch(() => undefined);
  }, [unreadIds]);

  const unread = notifications.filter((n) => unreadIds.has(n.id));
  const read = notifications.filter((n) => !unreadIds.has(n.id));
  const card = (notification: Notification) => (
    <li key={notification.id}>
      <NotificationCard notification={notification} unread={unreadIds.has(notification.id)}
        thanked={notification.answer !== null && thanked.has(notification.answer.id)}
        onThanked={(answerId) => setThanked((ids) => new Set(ids).add(answerId))} />
    </li>
  );

  return (
    <>
      <div role="group" aria-label={t("filter")} className="flex gap-1 border-b border-line">
        {(["all", "unread"] as const).map((value) => (
          <button key={value} type="button" aria-pressed={tab === value} onClick={() => setTab(value)}
            className={`-mb-px flex min-h-11 items-center gap-2 border-b-2 px-3 py-2 text-[16px] sm:px-5 ${tab === value ? "border-fei font-semibold" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t(`tabs.${value}`)}
            {value === "unread" && unread.length > 0 && (
              <span className="rounded-full bg-nav-active px-2 text-[13px] font-semibold text-muted-foreground">
                {unread.length}
              </span>
            )}
          </button>
        ))}
      </div>
      {tab === "unread" ? (
        unread.length === 0 ? <Notice text={t("emptyUnread")} /> : <ul className="grid gap-4">{unread.map(card)}</ul>
      ) : notifications.length === 0 && openQuestions === 0 ? (
        <Notice text={t("empty")} />
      ) : (
        <ul className="grid gap-4">
          {unread.map(card)}
          {openQuestions > 0 && (
            <li>
              <Link href="/questions"
                className="flex gap-3 rounded-[14px] border border-line bg-card px-4 py-4 hover:border-fei sm:gap-4 sm:px-6 sm:py-5">
                <span aria-hidden="true" className="grid size-9 shrink-0 place-items-center rounded-[10px] bg-sidebar">
                  <Users size={18} />
                </span>
                <span className="min-w-0">
                  <span className="block font-semibold">{t("openQuestions", { count: openQuestions })}</span>
                  <span className="mt-1 block text-muted-foreground">{t("openQuestionsText")}</span>
                  <span className="mt-1 block text-sm text-muted-foreground">{t("openQuestionsLink")}</span>
                </span>
              </Link>
            </li>
          )}
          {read.map(card)}
        </ul>
      )}
    </>
  );
}
