import type { Course } from "@/lib/api/client";

export function CourseHeader({ course }: { course: Course }) {
  return (
    <header className="border-line border-b pb-4">
      <h1 className="text-2xl font-semibold">{course.name}</h1>
      <p className="mt-1 text-muted-foreground">{course.code}</p>
    </header>
  );
}
