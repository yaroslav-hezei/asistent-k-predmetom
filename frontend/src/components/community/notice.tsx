import Link from "next/link";

/** A short message with an optional link: login prompt, empty list, not found, error. */
export function Notice({ text, link, role }: {
  text: string;
  link?: { href: string; label: string };
  role?: "alert";
}) {
  return (
    <div role={role} className="rounded-[14px] border border-dashed border-line-strong px-5 py-6 text-center text-muted-foreground">
      <p>{text}</p>
      {link && (
        <Link href={link.href} className="mt-3 inline-flex min-h-11 items-center rounded-lg bg-fei px-4 font-semibold text-on-fei hover:bg-fei/80">
          {link.label}
        </Link>
      )}
    </div>
  );
}
