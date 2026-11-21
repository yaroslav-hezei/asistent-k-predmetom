import { getTranslations } from "next-intl/server";
import { redirect } from "next/navigation";
import { LoginForm } from "@/components/login-form";
import { getMe } from "@/lib/auth/me";

export default async function LoginPage() {
  if (await getMe()) redirect("/chat");
  const t = await getTranslations("auth");
  return (
    <section className="mx-auto w-full max-w-[400px] px-5 py-8 md:py-16">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="mt-1 text-muted-foreground">{t("description")}</p>
      <LoginForm />
    </section>
  );
}
