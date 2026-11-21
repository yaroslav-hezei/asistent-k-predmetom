import createClient from "openapi-fetch";
import { authConfigured } from "@/lib/supabase/config";
import { createClient as createServerSupabase } from "@/lib/supabase/server";
import { API_URL } from "./client";
import type { paths } from "./schema";

/** The logged-in user's access token from the session cookies, or null. Server only. */
export async function sessionToken(): Promise<string | null> {
  if (!authConfigured) return null;
  const supabase = await createServerSupabase();
  // getSession() only reads the cookie. That is enough here: the token is just passed on and our
  // API verifies it. Never base decisions in the frontend on the session's user object.
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

/** An API client that sends `token` (if any) as the user's login. */
export function apiWithToken(token: string | null) {
  return createClient<paths>({
    baseUrl: API_URL,
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

/**
 * The API client for Server Components and Server Actions, with the logged-in user's token.
 * Create one per request. Without a login it sends no token.
 */
export async function serverApi() {
  return apiWithToken(await sessionToken());
}
