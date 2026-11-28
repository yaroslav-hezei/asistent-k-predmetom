"use client";

import { BadgeCheck, Pin } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useId, useState, useTransition } from "react";
import { RelativeTime } from "@/components/community/relative-time";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api/client";
import type { CourseNote } from "@/lib/api/teacher";

const NOTE_MAX = 4000; // the API's limit

/**
 * "Aktuálna informácia k predmetu": one text per course. The assistant uses it as verified,
 * with priority over the MAIS sheet, from the next question on; the sheet itself does not change.
 */
export function NoteEditor({ courseId, note }: { courseId: string; note: CourseNote | null }) {
  const t = useTranslations("verification");
  const router = useRouter();
  const id = useId();
  const [text, setText] = useState(note?.text ?? "");
  const [sending, setSending] = useState(false);
  const [showing, startTransition] = useTransition();
  const [status, setStatus] = useState<"saved" | "deleted" | "failed">();
  const pending = sending || showing;
  const trimmed = text.trim();
  const changed = trimmed !== (note?.text ?? "");

  async function run(action: "save" | "delete") {
    if (action === "delete" && !window.confirm(t("noteDeleteConfirm"))) return;
    setSending(true);
    setStatus(undefined);
    try {
      const params = { params: { path: { course_id: courseId } } };
      const { response } = action === "save"
        ? await api.PUT("/courses/{course_id}/note", { ...params, body: { text: trimmed } })
        : await api.DELETE("/courses/{course_id}/note", params);
      if (response.ok) {
        startTransition(() => {
          router.refresh();
          if (action === "delete") setText("");
          setStatus(action === "save" ? "saved" : "deleted");
        });
      } else {
        setStatus("failed");
      }
    } catch {
      setStatus("failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="rounded-[14px] border border-line bg-card px-4 py-4 sm:px-6 sm:py-5">
      <div className="flex items-center gap-2">
        <Pin size={18} aria-hidden="true" className="shrink-0" />
        <h2 id={`${id}-title`} className="flex-1 font-semibold">{t("noteTitle")}</h2>
        {note && (
          <span className="inline-flex items-center gap-1 rounded-full bg-ok-bg px-2.5 py-0.5 text-[13px] font-semibold text-ok-text">
            <BadgeCheck size={14} aria-hidden="true" />
            {t("verified")}
          </span>
        )}
      </div>
      <Textarea id={id} aria-labelledby={`${id}-title`} value={text} maxLength={NOTE_MAX} readOnly={pending}
        placeholder={t("notePlaceholder")}
        onChange={(event) => { setText(event.target.value); setStatus(undefined); }}
        className="mt-3 min-h-[110px] rounded-xl border-line-strong bg-white px-4 py-3 text-[16px] leading-relaxed md:text-[16px]" />
      {note && (
        <p className="mt-2 text-[13px] text-muted-foreground">
          {t("noteSavedBy", { nickname: note.author.nickname ?? "" })}{" "}
          <RelativeTime value={note.updated_at} />
        </p>
      )}
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
        <p className="flex-1 text-sm text-muted-foreground">{t("noteHint")}</p>
        <div className="flex shrink-0 gap-2">
          {note && (
            <Button type="button" variant="ghost" disabled={pending} onClick={() => run("delete")}
              className="h-11 px-4 text-[15px] text-warn-text hover:bg-warn-bg">
              {t("noteDelete")}
            </Button>
          )}
          <Button type="button" disabled={!trimmed || !changed || pending} onClick={() => run("save")}
            className="h-11 flex-1 px-5 text-[15px] font-semibold sm:flex-none">
            {pending ? t("saving") : t("save")}
          </Button>
        </div>
      </div>
      {status && (
        <p role={status === "failed" ? "alert" : "status"}
          className={`mt-2 text-sm ${status === "failed" ? "text-destructive" : "text-ok-text"}`}>
          {t(`noteStatus.${status}`)}
        </p>
      )}
    </section>
  );
}
