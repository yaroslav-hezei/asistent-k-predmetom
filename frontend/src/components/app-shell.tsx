"use client";

import { Bell, LogIn, Menu, MessageCircle, MessagesSquare, Plus, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useMe } from "@/components/me-provider";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { setLanguage } from "@/i18n/actions";
import { Avatar, BrandMark } from "@/components/account-marks";
import { AccountMenu } from "@/components/account-menu";
import { authConfigured } from "@/lib/supabase/config";

import { History } from "@/components/chat/history";
import { ChatTitleContext, type ChatTitle } from "@/components/chat/course-title";
import type { ChatSummary } from "@/lib/api/client";

const navigation = [
  { href: "/chat", key: "chat", Icon: MessageCircle },
  { href: "/questions", key: "questions", Icon: MessagesSquare },
  { href: "/notifications", key: "notifications", Icon: Bell },
] as const;

function Sidebar({ chats, onNavigate }: { chats: ChatSummary[]; onNavigate?: () => void }) {
  const t = useTranslations("layout");
  const locale = useLocale();
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col overflow-y-auto px-3 py-3.5">
      <Link href="/chat" onClick={onNavigate} className="flex min-h-11 items-center gap-2.5 px-1.5 pr-11 pt-1 pb-3.5 md:pr-1.5 text-[15.5px] font-bold tracking-[-0.01em]">
        <BrandMark />
        {t("brand")}
      </Link>
      <Link href="/chat" onClick={onNavigate} className="mb-1.5 flex min-h-11 items-center gap-2.5 rounded-[10px] px-2.5 py-[9px] font-semibold hover:bg-nav-active">
        <Plus className="size-[22px] rounded-full bg-fei p-0.5 text-on-fei" />
        {t("newChat")}
      </Link>
      <nav aria-label={t("navigation")} className="grid gap-0.5">
        {navigation.map(({ href, key, Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link key={key} href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
              className={`flex min-h-11 items-center gap-[11px] rounded-[10px] px-2.5 py-[9px] hover:bg-nav-active ${active ? "bg-nav-active font-medium shadow-[inset_3px_0_0_var(--color-fei)]" : ""}`}>
              <Icon size={18} />
              {t(`nav.${key}`)}
            </Link>
          );
        })}
      </nav>
      <History chats={chats} onNavigate={onNavigate} />
      <div className="mt-auto flex items-center gap-2 border-t border-line px-1.5 pt-3">
        <Account onNavigate={onNavigate} />
        <div className="ml-auto shrink-0">
          <div role="group" aria-label={t("language")} className="inline-flex overflow-hidden rounded-lg border border-line-strong text-xs font-semibold">
            {(["sk", "en"] as const).map((language) => (
              <form key={language} action={setLanguage.bind(null, language)}>
                <button type="submit" aria-pressed={locale === language}
                  className={`min-h-11 min-w-11 px-2 py-1 md:min-h-0 md:min-w-0 ${locale === language ? "bg-foreground text-white" : "text-muted-foreground hover:bg-nav-active"}`}>
                  {t(language)}
                </button>
              </form>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Account({ onNavigate }: { onNavigate?: () => void }) {
  const t = useTranslations("auth");
  const me = useMe();
  const row = "flex min-h-11 items-center gap-2.5 rounded-[10px] px-2.5";

  if (me) {
    return (
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <Avatar nickname={me.nickname} />
        <div className="min-w-0 flex-1 px-1">
          <p className="truncate font-medium">{me.nickname}</p>
          <p className="text-xs text-muted-foreground">{t(`roles.${me.role}`)}</p>
        </div>
      </div>
    );
  }
  if (!authConfigured) return null;
  return (
    <Link href="/login" onClick={onNavigate} className={`${row} font-medium hover:bg-nav-active`}>
      <LogIn size={18} aria-hidden="true" className="shrink-0" />
      {t("signIn")}
    </Link>
  );
}

export function AppShell({ children, chats }: { children: React.ReactNode; chats: ChatSummary[] }) {
  const t = useTranslations("layout");
  const study = useTranslations("study");
  const auth = useTranslations("auth");
  const pathname = usePathname();
  const [title, setTitle] = useState<ChatTitle | null>(null);
  const [open, setOpen] = useState(false);
  const page = navigation.find(({ href }) => pathname === href || pathname.startsWith(href + "/"));
  return (
    <div className="flex min-h-dvh">
      <aside className="sticky top-0 hidden h-dvh w-[280px] shrink-0 border-r border-line bg-sidebar md:block">
        <Sidebar chats={chats} />
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex h-[62px] items-center gap-3 px-5 font-semibold md:px-[26px]">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger aria-label={t("menu")} className="grid size-11 shrink-0 place-items-center rounded-lg hover:bg-nav-active md:hidden">
              <Menu size={20} />
            </SheetTrigger>
            <SheetContent side="left" aria-describedby={undefined} showCloseButton={false} className="data-[side=left]:w-[280px] bg-sidebar p-0">
              <SheetTitle className="sr-only">{t("navigation")}</SheetTitle>
              <button type="button" onClick={() => setOpen(false)} className="absolute right-2 top-3 grid size-11 place-items-center rounded-lg hover:bg-nav-active" aria-label={study("close")}><X size={18} /></button>
              <Sidebar chats={chats} onNavigate={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
          <span className="min-w-0 truncate">{title?.pathname === pathname ? title.name : pathname === "/login" ? auth("title") : page && (page.key === "chat" ? t("newChat") : t(`nav.${page.key}`))}</span>
          <AccountMenu />
        </header>
        <main><ChatTitleContext.Provider value={setTitle}>{children}</ChatTitleContext.Provider></main>
      </div>
    </div>
  );
}
