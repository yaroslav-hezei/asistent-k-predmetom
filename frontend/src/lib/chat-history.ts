import { cache } from "react";
import { getMe } from "@/lib/auth/me";
import { serverApi } from "@/lib/api/server";
import type { ChatSummary } from "@/lib/api/client";

export const getChatHistory = cache(async (): Promise<ChatSummary[]> => {
  if (!await getMe()) return [];
  try {
    const { data } = await (await serverApi()).GET("/chats");
    return data ?? [];
  } catch {
    return [];
  }
});
