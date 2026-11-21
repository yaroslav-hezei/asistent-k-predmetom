"use client";

import { createContext, useContext } from "react";
import type { Me } from "@/lib/api/client";

const MeContext = createContext<Me | null>(null);

/** Gives client components the logged-in user, loaded once on the server by the root layout. */
export function MeProvider({ me, children }: { me: Me | null; children: React.ReactNode }) {
  return <MeContext.Provider value={me}>{children}</MeContext.Provider>;
}

/** The logged-in user's profile, or null when nobody is logged in. */
export function useMe() {
  return useContext(MeContext);
}
