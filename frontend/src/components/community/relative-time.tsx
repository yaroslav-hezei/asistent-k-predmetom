"use client";

import { useFormatter, useNow } from "next-intl";

/** "pred 2 h" with the exact date and time as a tooltip. */
export function RelativeTime({ value }: { value: string }) {
  const format = useFormatter();
  // The first render uses the request time from the server (no hydration mismatch); then every minute.
  const now = useNow({ updateInterval: 60_000 });
  const date = new Date(value);
  // Something created after the page was loaded is "just now", never "in 2 min".
  const reference = date > now ? date : now;
  return (
    <time dateTime={value} className="whitespace-nowrap" title={format.dateTime(date, { dateStyle: "medium", timeStyle: "short" })}>
      {format.relativeTime(date, { now: reference, style: "short" })}
    </time>
  );
}

/** Whether the date is less than a day before now ("Nová"). */
export function useIsRecent(value: string) {
  const now = useNow({ updateInterval: 60_000 });
  return now.getTime() - new Date(value).getTime() < 24 * 60 * 60 * 1000;
}
