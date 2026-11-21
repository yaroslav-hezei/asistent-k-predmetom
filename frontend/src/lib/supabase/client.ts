import { createBrowserClient } from "@supabase/ssr";
import { supabaseKey, supabaseUrl } from "./config";

/** Supabase in the browser. The session lives in cookies, so the server sees it too. */
export function createClient() {
  return createBrowserClient(supabaseUrl, supabaseKey);
}
