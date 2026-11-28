import { getTranslations } from "next-intl/server";
import { getMe } from "@/lib/auth/me";
import { serverApi } from "@/lib/api/server";
import { ChatView } from "@/components/chat/chat-view";
import { ChatNotice } from "@/components/chat/chat-notice";

export default async function ChatPage({ params }: { params: Promise<{ chatId: string }> }) {
  const [t, me, { chatId }] = await Promise.all([getTranslations("chat"), getMe(), params]);
  if (!me) return <ChatNotice login />;

  const result = await (await serverApi()).GET("/chats/{chat_id}", {
    params: { path: { chat_id: chatId } },
  }).catch(() => null);

  if (result?.response.status === 401) return <ChatNotice login />;
  if (!result?.data) {
    const status = result?.response.status;
    return <ChatNotice message={status === 404 || status === 422 ? t("chatMissing") : t("error")} />;
  }

  const { id, course, messages } = result.data;
  return <ChatView key={id} course={course} pathname={"/chat/" + id} chatId={id} initialMessages={messages} userId={me.id} />;
}
