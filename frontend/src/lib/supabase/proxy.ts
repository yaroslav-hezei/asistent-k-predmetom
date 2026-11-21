import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { authConfigured, supabaseKey, supabaseUrl } from "./config";

/**
 * Keeps the login alive: when the access token (valid ~1 hour) has expired, Supabase exchanges the
 * refresh token for a new one and writes the new cookies into both the request (for this render)
 * and the response (for the browser). No page is protected here; pages decide that themselves.
 */
export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });
  if (!authConfigured) return response;

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });

  // Nothing may run between createServerClient and getClaims(): getClaims() is what refreshes an
  // expired session. Skipping it makes users get logged out at random.
  await supabase.auth.getClaims();

  // Return exactly this response: it carries the refreshed cookies. A different response object
  // would drop them and log the user out on the next request.
  return response;
}
