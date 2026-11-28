import createClient from "openapi-fetch";
import { authConfigured } from "@/lib/supabase/config";
import { createClient as createBrowserSupabase } from "@/lib/supabase/client";
import type { components, paths } from "./schema";

export type Program = components["schemas"]["Program"];
export type Course = components["schemas"]["CourseSummary"];
export type PlanCourse = components["schemas"]["ProgramCourse"];
export type Semester = PlanCourse["semester"];
export type Me = components["schemas"]["Me"];

export type ChatMessage = components["schemas"]["ChatMessage"];
export type ChatSummary = components["schemas"]["ChatSummary"];
export type Source = components["schemas"]["Source"];

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * The API client for browser code and for public data on the server (the catalogue).
 * In the browser it adds the logged-in user's token to every request. On the server it sends no
 * token: for user data on the server use `serverApi()` from `./server`.
 */
export const api = createClient<paths>({ baseUrl: API_URL, cache: "no-store" });

api.use({
  async onRequest({ request }) {
    if (typeof window === "undefined" || !authConfigured) return;
    // The token is only passed on; our API verifies it (signature, expiry) itself.
    const { data } = await createBrowserSupabase().auth.getSession();
    const token = data.session?.access_token;
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
});
