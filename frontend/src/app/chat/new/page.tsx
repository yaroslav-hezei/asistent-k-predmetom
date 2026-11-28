import { getTranslations } from "next-intl/server";
import { api } from "@/lib/api/client";
import { getMe } from "@/lib/auth/me";
import { ChatView } from "@/components/chat/chat-view";
import { ChatNotice } from "@/components/chat/chat-notice";

export default async function NewChat({ searchParams }: {
  searchParams: Promise<{ course?: string | string[] }>;
}) {
  const { course: id } = await searchParams;
  const [t, me, result] = await Promise.all([
    getTranslations("chat"),
    getMe(),
    typeof id === "string" && id
      ? api.GET("/courses/{course_id}", { params: { path: { course_id: id } } }).catch(() => null)
      : undefined,
  ]);

  if (!result?.data) {
    return <ChatNotice message={result === undefined || result?.response.status === 404 ? t("missing") : t("error")} />;
  }
  return <ChatView key={result.data.id} course={result.data} pathname="/chat/new" userId={me?.id} />;
}
