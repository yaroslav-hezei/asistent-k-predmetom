import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

export default getRequestConfig(async () => {
  const locale = (await cookies()).get("hip.locale")?.value === "en" ? "en" : "sk";
  return {
    locale,
    // the same zone on the server and in the browser: dates render alike (all users are in Slovakia)
    timeZone: "Europe/Bratislava",
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
