import type { NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/proxy";

// Next.js runs this before every matching request (Next.js 16 name for "middleware").
export async function proxy(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  // Everything except static files and images.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
