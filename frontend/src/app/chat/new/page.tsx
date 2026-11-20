import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { api } from "@/lib/api/client";
import { CourseHeader } from "@/components/course-header";

export default async function NewChat({ searchParams }: {
  searchParams: Promise<{ course?: string | string[] }>;
}) {
  const t = await getTranslations("chat");
  const { course: id } = await searchParams;
  const result = typeof id === "string" && id
    ? await api.GET("/courses/{course_id}", { params: { path: { course_id: id } } }).catch(() => null)
    : undefined;
  const course = result?.data;

  return (
    <section className="mx-auto w-full max-w-[760px] px-5 py-8">
      {course ? (
        <>
          <CourseHeader course={course} />
          <p className="mt-5 text-muted-foreground">{t("soon")}</p>
        </>
      ) : (
        <>
          <p>{result === undefined || result?.response.status === 404 ? t("missing") : t("error")}</p>
          <Link className="text-fei-dark mt-3 inline-block underline" href="/chat">{t("back")}</Link>
        </>
      )}
    </section>
  );
}
