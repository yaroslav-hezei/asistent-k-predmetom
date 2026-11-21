import { cache } from "react";
import type { Me } from "@/lib/api/client";
import { apiWithToken, sessionToken } from "@/lib/api/server";

/**
 * The logged-in user's profile from our API (`GET /me`), or null when nobody is logged in,
 * the token is invalid, the account has no profile or the API cannot be reached.
 * Server only; called at most once per request (React `cache`).
 */
export const getMe = cache(async (): Promise<Me | null> => {
  const token = await sessionToken();
  if (!token) return null; // not logged in: no need to ask the API
  try {
    const { data } = await apiWithToken(token).GET("/me");
    return data ?? null;
  } catch {
    return null;
  }
});
