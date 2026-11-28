import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

export default getRequestConfig(async () => {
  const locale = (await cookies()).get("hip.locale")?.value === "en" ? "en" : "sk";
  return {
    locale,
    // The same zone and "now" on the server and in the browser: dates and "pred 2 min" render
    // alike, no hydration mismatch (all users are in Slovakia; `useNow` moves on in the browser).
    timeZone: "Europe/Bratislava",
    now: new Date(),
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
