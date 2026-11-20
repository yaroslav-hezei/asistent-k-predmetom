import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

export default getRequestConfig(async () => {
  const locale = (await cookies()).get("hip.locale")?.value === "en" ? "en" : "sk";
  return { locale, messages: (await import(`../../messages/${locale}.json`)).default };
});
