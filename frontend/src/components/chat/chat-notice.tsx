import Link from "next/link";
import { useTranslations } from "next-intl";

export function ChatNotice({ message, login = false, draft }: { message?: string; login?: boolean; draft?: string }) {
  const t = useTranslations("chat");
  const auth = useTranslations("auth");
  return (
    <div className="mx-auto w-full max-w-[760px] px-5 py-8">
      <p>{login ? t("loginPrompt") : message}</p>
      <Link href={login ? "/login" : "/chat"} className="mt-3 inline-flex min-h-11 items-center rounded-lg bg-fei px-4 font-semibold text-on-fei">
        {login ? auth("signIn") : t("back")}
      </Link>
      {draft && <p className="mt-4 whitespace-pre-wrap wrap-anywhere rounded-xl bg-fei-soft p-3">{draft}</p>}
    </div>
  );
}
