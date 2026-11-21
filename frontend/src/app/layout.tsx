import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import { AppShell } from "@/components/app-shell";
import { MeProvider } from "@/components/me-provider";
import { getMe } from "@/lib/auth/me";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("layout");
  return { title: t("brand") };
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang={await getLocale()}>
      <body>
        <NextIntlClientProvider>
          <MeProvider me={await getMe()}>
            <AppShell>{children}</AppShell>
          </MeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
