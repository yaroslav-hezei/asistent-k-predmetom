"use client";

import { useTranslations } from "next-intl";
import type { Author } from "@/lib/api/community";
import { RelativeTime } from "./relative-time";

/** "tomas_r · pred 2 h" — a teacher is marked as such. */
export function AuthorLine({ author, createdAt }: { author: Author; createdAt: string }) {
  const t = useTranslations("questions");
  return (
    <>
      <span className="font-medium text-foreground/80">{author.nickname}</span>
      {author.kind === "vyucujuci" && <span> ({t("teacher")})</span>}
      <span aria-hidden="true"> · </span>
      <RelativeTime value={createdAt} />
    </>
  );
}
