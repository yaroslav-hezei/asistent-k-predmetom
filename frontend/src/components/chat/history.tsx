"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { usePathname } from "next/navigation";
import type { ChatSummary } from "@/lib/api/client";

export function courseMark(name: string) {
  return (name.match(/\p{L}{3,}/gu) ?? []).slice(0, 3).map(word => word[0]).join("").toUpperCase();
}

export function History({ chats, onNavigate }: { chats: ChatSummary[]; onNavigate?: () => void }) {
  const t = useTranslations("layout");
  const pathname = usePathname();

  if (!chats.length) return null;
  return (
    <nav aria-label={t("history")} className="my-4">
      <h2 className="px-2.5 pb-1 text-xs font-semibold text-muted-foreground">{t("history")}</h2>
      <ul>
        {chats.map(chat => {
          const href = "/chat/" + encodeURIComponent(chat.id);
          const active = pathname === href;
          return (
            <li key={chat.id}>
              <Link href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
                className={`flex min-h-11 items-center gap-2 rounded-[10px] px-2.5 text-sm hover:bg-nav-active ${active ? "bg-nav-active font-medium" : ""}`}>
                <span aria-hidden="true" className="min-w-8 rounded bg-fei-soft px-1 py-0.5 text-center text-[10px] font-semibold text-fei-dark">{courseMark(chat.course.name)}</span>
                <span className="truncate">{chat.title}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
