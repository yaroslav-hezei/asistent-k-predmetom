"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { authConfigured } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

/**
 * What the login form shows after a failed attempt: `error` is a key under `auth.errors` in the
 * messages; `email` refills the field (React clears the form after every submit).
 */
export type SignInState = { error: "invalid" | "failed" | "unavailable"; email: string } | null;

export async function signIn(_previous: SignInState, form: FormData): Promise<SignInState> {
  const email = String(form.get("email") ?? "").trim();
  const password = String(form.get("password") ?? "");
  if (!authConfigured) return { error: "unavailable", email };
  if (!email || !password) return { error: "invalid", email };

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: error.code === "invalid_credentials" ? "invalid" : "failed", email };

  // The session cookies are set; render everything again with the user known.
  revalidatePath("/", "layout");
  redirect("/chat");
}

export async function signOut() {
  if (authConfigured) {
    const supabase = await createClient();
    // "local": only this browser. The default ("global") would also log out the same test account
    // on every other device, e.g. during a demo.
    await supabase.auth.signOut({ scope: "local" });
  }
  revalidatePath("/", "layout");
  redirect("/chat");
}
