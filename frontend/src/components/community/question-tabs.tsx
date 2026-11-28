import { getTranslations } from "next-intl/server";
import Link from "next/link";
import type { QuestionList, QuestionStatus } from "@/lib/api/community";
import { questionsHref } from "./links";

/** "Otvorené 3 | Zodpovedané 12": links, so every tab has its own URL. */
export async function QuestionTabs({ counts, courseId, tab }: {
  counts: QuestionList["counts"];
  courseId: string | null;
  tab: QuestionStatus;
}) {
  const t = await getTranslations("questions");
  return (
    <nav aria-label={t("tabsLabel")} className="flex gap-1 border-b border-line">
      {(["open", "answered"] as const).map((status) => {
        const active = status === tab;
        return (
          <Link key={status} href={questionsHref(courseId, status)} aria-current={active ? "page" : undefined}
            className={`-mb-px flex min-h-11 items-center gap-2 border-b-2 px-3 py-2 text-[16px] sm:px-5 ${active ? "border-fei font-semibold" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t(`tabs.${status}`)}
            <span className="rounded-full bg-nav-active px-2 text-[13px] font-semibold text-muted-foreground">
              {counts[status]}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
