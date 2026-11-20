import { getTranslations } from "next-intl/server";

export async function ComingSoon({ page }: { page: "questions" | "notifications" }) {
  const t = await getTranslations();
  return (
    <section className="mx-auto w-full max-w-[840px] px-5 py-8">
      <h1 className="text-2xl font-semibold">{t(`layout.nav.${page}`)}</h1>
      <p className="mt-3 text-muted-foreground">{t("placeholder.soon")}</p>
    </section>
  );
}
