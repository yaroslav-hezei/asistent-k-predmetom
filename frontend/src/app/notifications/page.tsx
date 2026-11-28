import { getTranslations } from "next-intl/server";
import { Notice } from "@/components/community/notice";
import { QuestionsLayout } from "@/components/community/questions-layout";
import { NotificationsView } from "@/components/notifications/notifications-view";
import { serverApi } from "@/lib/api/server";
import { getMe } from "@/lib/auth/me";

export default async function NotificationsPage() {
  const t = await getTranslations("notifications");
  const login = <Notice text={t("loginPrompt")} link={{ href: "/login", label: t("signIn") }} />;
  const me = await getMe();
  if (!me) return <QuestionsLayout>{login}</QuestionsLayout>;
  const client = await serverApi();
  const loaded = await Promise.all([client.GET("/notifications"), client.GET("/badges")]).catch(() => null);
  if (!loaded) return <QuestionsLayout><Notice role="alert" text={t("error")} /></QuestionsLayout>;
  const [notifications, badges] = loaded;
  if (notifications.response.status === 401) return <QuestionsLayout>{login}</QuestionsLayout>;
  if (!notifications.data) return <QuestionsLayout><Notice role="alert" text={t("error")} /></QuestionsLayout>;

  return (
    <QuestionsLayout>
      <h1 className="sr-only">{t("title")}</h1>
      <NotificationsView notifications={notifications.data} openQuestions={badges.data?.open_questions ?? 0} />
    </QuestionsLayout>
  );
}
