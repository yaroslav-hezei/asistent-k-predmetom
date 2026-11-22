"use client";

import { useTranslations } from "next-intl";
import { useActionState, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { signIn, type SignInState } from "@/lib/auth/actions";
import { demoAccounts, demoPasswords } from "@/lib/demo-accounts";

const input =
  "h-11 w-full rounded-lg border border-line-strong bg-white px-3 text-[16px] font-normal outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive";

export function LoginForm() {
  const t = useTranslations("auth");
  const [state, action, pending] = useActionState<SignInState, FormData>(signIn, null);
  const [demo, setDemo] = useState("");
  const [email, setEmail] = useState("");
  const password = useRef<HTMLInputElement>(null);
  const invalid = state?.error === "invalid" || undefined;

  function chooseDemo(nickname: string) {
    const account = demoAccounts.find((item) => item.nickname === nickname);
    if (!account) return;
    setDemo(nickname);
    setEmail(account.email);
    if (password.current) password.current.value = demoPasswords[account.role];
  }

  return (
    <form action={action} onSubmit={() => setDemo("")} className="mt-5 grid gap-4">
      <div className="grid gap-2 rounded-xl bg-fei-soft p-3">
        <p className="text-sm font-semibold">{t("demoTitle")}</p>
        <p className="text-sm">{t("demoDescription")}</p>
        <NativeSelect aria-label={t("demoChoose")} disabled={pending} value={demo}
          className="w-full [&>select]:h-11 [&>select]:bg-card [&>select]:text-[16px]"
          onChange={(event) => chooseDemo(event.target.value)}>
          <NativeSelectOption value="" disabled>{t("demoChoose")}</NativeSelectOption>
          {demoAccounts.map((account) => (
            <NativeSelectOption key={account.nickname} value={account.nickname}>
              {account.nickname} — {account.year === null ? t("demoTeacher") : t("demoYear", { year: account.year })}
            </NativeSelectOption>
          ))}
        </NativeSelect>
      </div>
      <label className="grid gap-1.5 font-medium">
        {t("email")}
        <input name="email" type="email" required autoComplete="username"
          autoCapitalize="none" spellCheck={false} value={email} onChange={(event) => {
            setEmail(event.target.value);
            setDemo("");
          }}
          readOnly={pending} aria-invalid={invalid} className={input} />
      </label>
      <label className="grid gap-1.5 font-medium">
        {t("password")}
        <input ref={password} name="password" type="password" required autoComplete="current-password"
          onChange={() => setDemo("")} readOnly={pending}
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
