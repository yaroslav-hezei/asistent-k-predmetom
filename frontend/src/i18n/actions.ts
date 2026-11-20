"use server";

import { cookies } from "next/headers";

export async function setLanguage(locale: string) {
  if (locale !== "sk" && locale !== "en") return;
  (await cookies()).set("hip.locale", locale, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
    httpOnly: true,
  });
}
