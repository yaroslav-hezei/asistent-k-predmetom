"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import type { Course } from "@/lib/api/client";
import type { QuestionStatus } from "@/lib/api/community";
import { questionsHref } from "./links";

/** "Predmet: …" — all my courses, or one of them. */
export function CourseFilter({ courses, courseId, tab }: {
  courses: Course[];
  courseId: string | null;
  tab: QuestionStatus;
}) {
  const t = useTranslations("questions");
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <label className="inline-flex h-11 max-w-full items-center rounded-[10px] border border-line-strong bg-card pl-3.5 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
      <span className="shrink-0 text-muted-foreground">{t("course")}:</span>
      <NativeSelect value={courseId ?? ""} disabled={pending}
        onChange={(event) => startTransition(() => router.push(questionsHref(event.target.value || null, tab)))}
        className="min-w-0 [&>select]:h-10 [&>select]:max-w-full [&>select]:truncate [&>select]:border-0 [&>select]:pl-1.5 [&>select]:text-[16px] [&>select]:font-medium [&>select]:focus-visible:ring-0 md:[&>select]:text-[15px]">
        <NativeSelectOption value="">{t("allCourses")}</NativeSelectOption>
        {courses.map((course) => (
          <NativeSelectOption key={course.id} value={course.id}>{course.name}</NativeSelectOption>
        ))}
      </NativeSelect>
    </label>
  );
}
