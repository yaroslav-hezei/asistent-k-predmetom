"use client";

import { ArrowUp } from "lucide-react";
import { useTranslations } from "next-intl";
import { useLayoutEffect, useRef } from "react";

const limit = 1000;

export function Composer({ value, onChange, onSend, busy, error }: {
  value: string;
  onChange: (value: string) => void;
  onSend: (question: string) => void;
  busy: boolean;
  error: boolean;
}) {
  const t = useTranslations("chat");
  const input = useRef<HTMLTextAreaElement>(null);
  const question = value.trim();
  const length = Array.from(question).length;
  const disabled = busy || length < 3 || length > limit;

  useLayoutEffect(() => {
    if (!input.current) return;
    input.current.style.height = "auto";
    input.current.style.height = input.current.scrollHeight + "px";
  }, [value]);

  return (
    <form className="shrink-0 border-t border-line bg-background px-4 pt-3 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:px-5"
      onSubmit={event => {
        event.preventDefault();
        if (!disabled) onSend(question);
      }}>
      {error && <p role="alert" className="mb-2 text-sm text-warn-text">{t("sendError")}</p>}
      <div className="flex items-end gap-2 rounded-2xl border border-line-strong bg-card p-2 focus-within:ring-2 focus-within:ring-fei">
        <textarea ref={input} rows={1} value={value} disabled={busy} aria-label={t("placeholder")}
          placeholder={t("placeholder")}
          className="max-h-36 min-h-11 group-data-compact/chat:max-h-20 min-w-0 flex-1 resize-none bg-transparent px-2 py-2.5 text-base leading-6 outline-none"
          onChange={event => {
            const next = event.target.value;
            if (Array.from(next.trim()).length <= limit && next.length <= limit * 4) onChange(next);
          }}
          onKeyDown={event => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && matchMedia("(pointer: fine)").matches) {
              event.preventDefault();
              if (!disabled) onSend(question);
            }
          }} />
        <button type="submit" disabled={disabled} aria-label={t("send")}
          className="grid size-11 shrink-0 place-items-center rounded-full bg-fei text-on-fei disabled:opacity-50">
          <ArrowUp size={21} aria-hidden="true" />
        </button>
      </div>
      {length >= limit - 100 && <p className="mt-1 text-right text-xs text-muted-foreground">{t("counter", { length, limit })}</p>}
      <p className="mt-2 text-center text-xs text-muted-foreground">{t("disclaimer")}</p>
    </form>
  );
}
