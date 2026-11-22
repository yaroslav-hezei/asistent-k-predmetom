import { getTranslations } from "next-intl/server";
import { redirect } from "next/navigation";
import { BrandMark } from "@/components/account-marks";
import { LoginForm } from "@/components/login-form";
import { getMe } from "@/lib/auth/me";
import { authConfigured } from "@/lib/supabase/config";

export default async function LoginPage() {
  if (!authConfigured || await getMe()) redirect("/chat");
  const t = await getTranslations("auth");
  const layout = await getTranslations("layout");

  return (
    <div className="grid min-h-[calc(100dvh-62px)] place-items-center px-5 py-6">
      <section className="w-full max-w-[400px] rounded-2xl border border-line bg-card p-5 shadow-sm sm:p-7">
        <div className="mb-5 flex items-center gap-2.5 font-bold">
          <BrandMark />
          {layout("brand")}
        </div>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("description")}</p>
        <LoginForm />
      </section>
    </div>
  );
}
