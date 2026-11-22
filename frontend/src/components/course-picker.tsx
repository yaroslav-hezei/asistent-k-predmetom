"use client";

import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMe } from "@/components/me-provider";
import { Button } from "@/components/ui/button";
import { api, type Course, type Me, type PlanCourse, type Program } from "@/lib/api/client";
import { StudyDialog, type StudyChoice, useProgramLabel } from "./study-dialog";

const storageKey = "hip.myCourses";
type RequestState<T> = { key: string; data: T | null };
const cardClass = "block rounded-xl border border-line bg-card px-3.5 py-3 hover:border-fei";

function getSavedChoice(programs: Program[]): StudyChoice | null {
  try {
    return validateChoice(programs, JSON.parse(localStorage.getItem(storageKey) ?? "null"));
  } catch {
    // Storage can be unavailable or contain an obsolete value.
  }
  return null;
}

function validateChoice(programs: Program[], choice: StudyChoice | null): StudyChoice | null {
  const program = programs.find(({ id }) => id === choice?.programId);
  if (choice && program && Number.isInteger(choice.year) && choice.year >= 1 &&
    choice.year <= program.years && (choice.semester === "ZS" || choice.semester === "LS")) {
    return { programId: program.id, year: choice.year, semester: choice.semester };
  }
  return null;
}

function courseHref(id: string) {
  return `/chat/new?course=${encodeURIComponent(id)}`;
}

export function CoursePicker() {
  const me = useMe();
  return <CoursePickerContent key={me?.id ?? "guest"} me={me} />;
}

function CoursePickerContent({ me }: { me: Me | null }) {
  const router = useRouter();
  const t = useTranslations("picker");
  const study = useTranslations("study");
  const programLabel = useProgramLabel();
  const [programs, setPrograms] = useState<Program[] | null | undefined>();
  const [visitorChoice, setVisitorChoice] = useState<StudyChoice | null>(null);
  const [savedProfile, setSavedProfile] = useState<{ previous: Me; study: Me["study"] }>();
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<"saveInvalid" | "saveFailed">();
  const isGuest = me === null;
  const profileStudy = savedProfile && savedProfile.previous === me ? savedProfile.study : me?.study;
  const choice = useMemo(() => {
    if (!programs) return null;
    if (isGuest) return visitorChoice;
    return validateChoice(programs, profileStudy ? {
      programId: profileStudy.program_id,
      year: profileStudy.year,
      semester: profileStudy.semester,
    } : null);
  }, [programs, isGuest, visitorChoice, profileStudy]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const studyButton = useRef<HTMLButtonElement>(null);
  const [input, setInput] = useState("");
  const [search, setSearch] = useState<RequestState<Course[]>>();
  const [plan, setPlan] = useState<RequestState<PlanCourse[]>>();
  const query = input.trim();
  const planKey = choice ? `${choice.programId}/${choice.year}/${choice.semester}` : "";
  const program = programs?.find(({ id }) => id === choice?.programId);
  const results = search?.key === query ? search.data : undefined;
  const courses = plan?.key === planKey ? plan.data : undefined;

  useEffect(() => {
    const controller = new AbortController();
    api.GET("/programs", { signal: controller.signal }).then(({ data }) => {
      if (controller.signal.aborted) return;
      setPrograms(data ?? null);
      if (data && isGuest) setVisitorChoice(getSavedChoice(data));
    }).catch(() => {
      if (!controller.signal.aborted) setPrograms(null);
    });
    return () => controller.abort();
  }, [isGuest]);

  useEffect(() => {
    if (query.length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.GET("/courses", {
          params: { query: { q: query } },
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setSearch({ key: query, data: data ?? null });
      } catch {
        if (!controller.signal.aborted) setSearch({ key: query, data: null });
      }
    }, 275);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  useEffect(() => {
    if (!choice) return;
    const controller = new AbortController();
    api.GET("/programs/{program_id}/courses", {
      params: {
        path: { program_id: choice.programId },
        query: { year: choice.year, semester: choice.semester },
      },
      signal: controller.signal,
    }).then(({ data }) => {
      if (!controller.signal.aborted) setPlan({ key: planKey, data: data ?? null });
    }).catch(() => {
      if (!controller.signal.aborted) setPlan({ key: planKey, data: null });
    });
    return () => controller.abort();
  }, [choice, planKey]);

  async function saveChoice(next: StudyChoice) {
    setSaveError(undefined);
    if (me) {
      setSaving(true);
      try {
        const { data, response } = await api.PATCH("/me", {
          body: { program_id: next.programId, year: next.year, semester: next.semester },
        });
        if (!data) {
          setSaveError(response.status === 422 ? "saveInvalid" : "saveFailed");
          return;
        }
        setSavedProfile({ previous: me, study: data.study });
        router.refresh();
      } catch {
        setSaveError("saveFailed");
        return;
      } finally {
        setSaving(false);
      }
    } else {
      try {
        localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        // The selection remains usable for this visit.
      }
      setVisitorChoice(next);
    }
    closeDialog();
  }

  function closeDialog() {
    setSaveError(undefined);
    setDialogOpen(false);
    requestAnimationFrame(() => studyButton.current?.focus());
  }

  return (
    <div className="mx-auto w-full max-w-[760px] px-5 pt-12 pb-10 md:pt-24">
      <h1 className="mb-7 text-center text-2xl leading-[1.5] font-bold tracking-[-0.01em] md:text-[32px]">{t("title")}</h1>
      <label className="flex items-center gap-3 rounded-2xl border border-line-strong bg-card px-[18px] py-4 text-muted-foreground shadow-[0_2px_10px_rgb(0_0_0/0.04)] focus-within:ring-2 focus-within:ring-fei">
        <Search aria-hidden="true" size={20} className="shrink-0" />
        <input type="search" className="w-full min-w-0 text-foreground outline-none placeholder:text-muted-foreground"
          aria-label={t("search")} placeholder={t("search")} value={input}
          onChange={(event) => {
            if (event.target.value.trim() !== query) setSearch(undefined);
            setInput(event.target.value);
          }} />
      </label>

      {query.length >= 2 ? (
        <section aria-label={t("results")} className="mt-[30px]">
          <h2 className="mb-3 text-sm font-semibold">{t("results")}</h2>
          {results === undefined && <p role="status">{t("loading")}</p>}
          {results === null && <p role="alert">{t("error")}</p>}
          {results?.length === 0 && <p role="status">{t("noResults")}</p>}
          {results && results.length > 0 && (
            <ul className="divide-y divide-line rounded-xl border border-line bg-card">
              {results.map((course) => (
                <li key={course.id}>
                  <Link className="block rounded-lg px-3.5 py-3 hover:bg-fei-soft" href={courseHref(course.id)}>
                    <span className="block font-medium">{course.name}</span>
                    <span className="text-[13px] text-muted-foreground">
                      {course.code} · {course.semesters.map((semester) => study(semester)).join(", ") || t("noSemester")}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : (
        <section aria-labelledby="my-courses" className="mt-[30px]">
          <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
            <h2 id="my-courses" className="font-semibold">{t("myCourses")}</h2>
            {choice && program && (
              <>
                <p className="text-[13px] text-muted-foreground">
                  {programLabel(program)} · {t("yearSemester", { year: choice.year, semester: study(choice.semester) })}
                </p>
                <button ref={studyButton} type="button" className="text-[13px] font-medium text-fei-dark hover:underline" onClick={() => setDialogOpen(true)}>
                  {t("change")}
                </button>
              </>
            )}
          </div>
          {programs === undefined && <p role="status">{t("loading")}</p>}
          {programs === null && <p role="alert">{t("error")}</p>}
          {programs && !program && (
            <div className="rounded-xl border border-line bg-card p-4">
              <p className="mb-3 text-muted-foreground">{t("invite")}</p>
              <Button ref={studyButton} onClick={() => setDialogOpen(true)}>{t("choose")}</Button>
            </div>
          )}
          {choice && program && (
            <>
              {courses === undefined && <p role="status">{t("loading")}</p>}
              {courses === null && <p role="alert">{t("error")}</p>}
              {courses?.length === 0 && <p role="status">{t("empty")}</p>}
              {courses && courses.length > 0 && (
                <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                  {courses.map(({ course, year, semester }) => (
                    <li key={course.id}>
                      <Link href={courseHref(course.id)} className={`${cardClass} h-full`}>
                        <span className="block text-[14.5px] font-medium">{course.name}</span>
                        <span className="text-[12.5px] text-muted-foreground">
                          {t("yearSemester", { year, semester: study(semester) })}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      )}
      <p className="mt-[26px] text-center text-[13px] text-muted-foreground">{t("hint")}</p>
      {dialogOpen && programs && (
        <StudyDialog programs={programs} initial={choice} onSave={saveChoice} onClose={closeDialog}
          saving={saving} error={saveError && t(saveError)} />
      )}
    </div>
  );
}
