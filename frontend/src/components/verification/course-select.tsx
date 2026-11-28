"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import type { TeacherCourse } from "@/lib/api/teacher";

/** "Predmet: …" — the courses the teacher verifies, with the answers waiting in each. */
export function CourseSelect({ courses, courseId }: { courses: TeacherCourse[]; courseId: string }) {
  const t = useTranslations("verification");
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <label className="inline-flex h-11 max-w-full items-center rounded-[10px] border border-line-strong bg-card pl-3.5 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
      <span className="shrink-0 text-muted-foreground">{t("course")}:</span>
      <NativeSelect value={courseId} disabled={pending}
        onChange={(event) => startTransition(() =>
          router.push(`/verification?course=${encodeURIComponent(event.target.value)}`))}
        className="min-w-0 [&>select]:h-10 [&>select]:max-w-full [&>select]:truncate [&>select]:border-0 [&>select]:pl-1.5 [&>select]:text-[16px] [&>select]:font-medium [&>select]:focus-visible:ring-0 md:[&>select]:text-[15px]">
        {courses.map(({ course, unverified_answers: count }) => (
          <NativeSelectOption key={course.id} value={course.id}>
            {count > 0 ? t("courseWithCount", { name: course.name, count }) : course.name}
          </NativeSelectOption>
        ))}
      </NativeSelect>
    </label>
  );
}
