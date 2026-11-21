"use client";

import { Bell, BookOpen, LogIn, LogOut, Menu, MessageCircle, MessagesSquare, Plus } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useMe } from "@/components/me-provider";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { setLanguage } from "@/i18n/actions";
import { signOut } from "@/lib/auth/actions";
import { authConfigured } from "@/lib/supabase/config";

const navigation = [
  { href: "/chat", key: "chat", Icon: MessageCircle },
  { href: "/questions", key: "questions", Icon: MessagesSquare },
  { href: "/notifications", key: "notifications", Icon: Bell },
] as const;

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const t = useTranslations("layout");
  const locale = useLocale();
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col px-3 py-3.5">
      <Link href="/chat" onClick={onNavigate} className="flex items-center gap-2.5 px-1.5 pt-1 pb-3.5 text-[15.5px] font-bold tracking-[-0.01em]">
        <span className="grid size-[30px] place-items-center rounded-[9px] bg-fei text-on-fei"><BookOpen size={17} /></span>
        {t("brand")}
      </Link>
      <Link href="/chat" onClick={onNavigate} className="mb-1.5 flex items-center gap-2.5 rounded-[10px] px-2.5 py-[9px] font-semibold hover:bg-nav-active">
        <Plus className="size-[22px] rounded-full bg-fei p-0.5 text-on-fei" />
        {t("newChat")}
      </Link>
      <nav aria-label={t("navigation")} className="grid gap-0.5">
        {navigation.map(({ href, key, Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link key={key} href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
              className={`flex items-center gap-[11px] rounded-[10px] px-2.5 py-[9px] hover:bg-nav-active ${active ? "bg-nav-active font-medium shadow-[inset_3px_0_0_var(--color-fei)]" : ""}`}>
              <Icon size={18} />
              {t(`nav.${key}`)}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto border-t border-line px-1.5 pt-3">
        <Account onNavigate={onNavigate} />
        <div className="flex justify-end">
          <div role="group" aria-label={t("language")} className="inline-flex overflow-hidden rounded-lg border border-line-strong text-xs font-semibold">
            {(["sk", "en"] as const).map((language) => (
              <form key={language} action={setLanguage.bind(null, language)}>
                <button type="submit" aria-pressed={locale === language}
                  className={`px-2 py-1 ${locale === language ? "bg-foreground text-white" : "text-muted-foreground hover:bg-nav-active"}`}>
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

/** Who is logged in, with "log out"; or a "log in" link. Nothing when login is not configured. */
function Account({ onNavigate }: { onNavigate?: () => void }) {
  const t = useTranslations("auth");
  const me = useMe();
  const row = "flex min-h-11 items-center gap-2.5 rounded-[10px] px-2.5";

  if (me) {
    return (
      <div className="mb-3 flex items-center gap-2">
        <div className="min-w-0 flex-1 px-1">
          <p className="truncate font-medium">{me.nickname}</p>
          <p className="text-xs text-muted-foreground">{t(`roles.${me.role}`)}</p>
        </div>
        <form action={signOut}>
          <button type="submit" className={`${row} text-muted-foreground hover:bg-nav-active hover:text-foreground`}>
            <LogOut size={18} />
            {t("signOut")}
          </button>
        </form>
      </div>
    );
  }
  if (!authConfigured) return null;
  return (
    <Link href="/login" onClick={onNavigate} className={`${row} mb-3 font-medium hover:bg-nav-active`}>
      <LogIn size={18} />
      {t("signIn")}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations("layout");
  const study = useTranslations("study");
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const page = navigation.find(({ href }) => pathname === href || pathname.startsWith(href + "/"));
  return (
    <div className="flex min-h-dvh">
      <aside className="sticky top-0 hidden h-dvh w-[280px] shrink-0 border-r border-line bg-sidebar md:block">
        <Sidebar />
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex h-[62px] items-center gap-3 px-5 font-semibold md:px-[26px]">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger aria-label={t("menu")} className="rounded-lg p-2 hover:bg-nav-active md:hidden">
              <Menu size={20} />
            </SheetTrigger>
            <SheetContent side="left" aria-describedby={undefined} showCloseButton={false} className="data-[side=left]:w-[280px] bg-sidebar p-0">
              <SheetTitle className="sr-only">{t("navigation")}</SheetTitle>
              <button type="button" onClick={() => setOpen(false)} className="absolute right-2 top-3 rounded px-2 py-1 text-sm hover:bg-nav-active" aria-label={study("close")}>×</button>
              <Sidebar onNavigate={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
          {page && (page.key === "chat" ? t("newChat") : t(`nav.${page.key}`))}
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
