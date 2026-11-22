"use client";

import { LogIn, LogOut } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useTransition } from "react";
import { Avatar } from "@/components/account-marks";
import { useMe } from "@/components/me-provider";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { signOut } from "@/lib/auth/actions";
import { authConfigured } from "@/lib/supabase/config";

export function AccountMenu() {
  const t = useTranslations("auth");
  const me = useMe();
  const [pending, startTransition] = useTransition();

  if (!authConfigured) return null;
  if (!me) {
    return (
      <Link href="/login" className="ml-auto flex min-h-11 min-w-11 shrink-0 items-center gap-1.5 rounded-lg px-2 text-sm hover:bg-nav-active">
        <LogIn aria-hidden="true" size={17} />
        {t("signIn")}
      </Link>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger aria-label={t("account")} disabled={pending}
        className="ml-auto grid size-11 shrink-0 place-items-center rounded-full hover:bg-nav-active md:size-8">
        <Avatar nickname={me.nickname} compact />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={6} className="w-52 max-w-(--available-width)">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="grid gap-0.5 px-2 py-1.5">
            <span className="truncate text-sm font-semibold text-foreground">{me.nickname}</span>
            <span className="text-xs text-muted-foreground">{t(`roles.${me.role}`)}</span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled={pending} onClick={() => startTransition(signOut)}
          className="flex min-h-11 cursor-default items-center gap-2 rounded-md px-2 outline-none data-highlighted:bg-nav-active md:min-h-8">
          <LogOut aria-hidden="true" size={16} />
          {t("signOut")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
