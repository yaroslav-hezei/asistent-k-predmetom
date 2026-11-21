"use client";

import { useTranslations } from "next-intl";
import { useActionState } from "react";
import { Button } from "@/components/ui/button";
import { signIn, type SignInState } from "@/lib/auth/actions";

// 16px text: iPhone Safari zooms into any input with a smaller font. 44px high: easy to tap.
const input =
  "h-11 w-full rounded-lg border border-line-strong bg-white px-3 text-[16px] font-normal outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive";

export function LoginForm() {
  const t = useTranslations("auth");
  const [state, action, pending] = useActionState<SignInState, FormData>(signIn, null);
  const invalid = state?.error === "invalid" || undefined;

  return (
    <form action={action} className="mt-6 grid gap-4">
      <label className="grid gap-1.5 font-medium">
        {t("email")}
        <input key={state?.email} name="email" type="email" required autoComplete="username"
          autoCapitalize="none" spellCheck={false} defaultValue={state?.email} aria-invalid={invalid}
          className={input} />
      </label>
      <label className="grid gap-1.5 font-medium">
        {t("password")}
        <input name="password" type="password" required autoComplete="current-password"
          aria-invalid={invalid} className={input} />
      </label>
      {state?.error && (
        <p role="alert" className="text-sm text-destructive">{t(`errors.${state.error}`)}</p>
      )}
      <Button type="submit" disabled={pending} className="h-11 w-full text-[15px] font-semibold">
        {pending ? t("submitting") : t("submit")}
      </Button>
    </form>
  );
}
