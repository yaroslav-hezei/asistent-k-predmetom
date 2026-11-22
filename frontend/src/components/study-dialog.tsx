"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { NativeSelect, NativeSelectOption, NativeSelectOptGroup } from "@/components/ui/native-select";
import type { Program, Semester } from "@/lib/api/client";

const degrees = ["bc", "bc_po", "ing"] as const;
export const semesters = ["ZS", "LS"] as const;

export type StudyChoice = { programId: string; year: number; semester: Semester };

export function useProgramLabel() {
  const t = useTranslations("study");
  return (program: Program) => {
    const details = [t(program.degree)];
    if (program.language === "en") details.push(t("en"));
    if (program.method === "kombinovana") details.push(t("combined"));
    return `${program.name} (${details.join(", ")})`;
  };
}

export function StudyDialog({ programs, initial, onClose, onSave, saving, error }: {
  programs: Program[];
  initial: StudyChoice | null;
  saving: boolean;
  error?: string;
  onClose: () => void;
  onSave: (choice: StudyChoice) => void;
}) {
  const t = useTranslations("study");
  const label = useProgramLabel();
  const [programId, setProgramId] = useState(initial?.programId ?? "");
  const [year, setYear] = useState(initial?.year ?? 1);
  const [semester, setSemester] = useState<Semester>(initial?.semester ?? "ZS");
  const program = programs.find(({ id }) => id === programId);

  return (
    <Dialog open onOpenChange={(open) => { if (!open && !saving) onClose(); }}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>{t("description")}</DialogDescription>
        </DialogHeader>
        <form className="grid min-w-0 gap-4" onSubmit={(event) => {
          event.preventDefault();
          if (program && !saving) onSave({ programId, year, semester });
        }}>
          <label className="grid min-w-0 gap-1.5 font-medium">
            {t("program")}
            <NativeSelect className="w-full" required value={programId} onChange={(event) => {
              setProgramId(event.target.value);
              setYear(1);
            }}>
              <NativeSelectOption value="" disabled>{t("select")}</NativeSelectOption>
              {degrees.map((degree) => (
                <NativeSelectOptGroup key={degree} label={t(degree)}>
                  {programs.filter((item) => item.degree === degree).map((item) => (
                    <NativeSelectOption key={item.id} value={item.id}>{label(item)}</NativeSelectOption>
                  ))}
                </NativeSelectOptGroup>
              ))}
            </NativeSelect>
          </label>
          <div className="grid grid-cols-[1fr_1.6fr] gap-3">
            <label className="grid min-w-0 gap-1.5 font-medium">
              {t("year")}
              <NativeSelect className="w-full" disabled={!program} value={year} onChange={(event) => setYear(Number(event.target.value))}>
                {Array.from({ length: program?.years ?? 1 }, (_, index) => (
                  <NativeSelectOption key={index + 1} value={index + 1}>{index + 1}</NativeSelectOption>
                ))}
              </NativeSelect>
            </label>
            <label className="grid min-w-0 gap-1.5 font-medium">
              {t("semester")}
              <NativeSelect className="w-full" value={semester} onChange={(event) => {
                setSemester(event.target.value === "LS" ? "LS" : "ZS");
              }}>
                {semesters.map((value) => <NativeSelectOption key={value} value={value}>{t(value)}</NativeSelectOption>)}
              </NativeSelect>
            </label>
          </div>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" disabled={saving} onClick={onClose}>{t("cancel")}</Button>
            <Button type="submit" disabled={!program || saving}>{t("save")}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
