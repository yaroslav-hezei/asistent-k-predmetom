import { getTranslations } from "next-intl/server";
import { CourseFilter } from "@/components/community/course-filter";
import { Notice } from "@/components/community/notice";
import { QuestionCard } from "@/components/community/question-card";
import { QuestionTabs } from "@/components/community/question-tabs";
import { QuestionsLayout } from "@/components/community/questions-layout";
import type { QuestionStatus } from "@/lib/api/community";
import { serverApi } from "@/lib/api/server";
import { getMe } from "@/lib/auth/me";
import { myCourses } from "./data";

export default async function QuestionsPage({ searchParams }: {
  searchParams: Promise<{ course?: string | string[]; tab?: string | string[] }>;
}) {
  const t = await getTranslations("questions");
  const me = await getMe();
  if (!me) {
    return (
      <QuestionsLayout>
        <Notice text={t("loginPrompt")} link={{ href: "/login", label: t("signIn") }} />
      </QuestionsLayout>
    );
  }
  const { course, tab: tabParam } = await searchParams;
  const courseId = typeof course === "string" && course ? course : null;
  const tab: QuestionStatus = tabParam === "answered" ? "answered" : "open";
  const client = await serverApi();
  const loaded = await Promise.all([
    client.GET("/questions", { params: { query: { course_id: courseId ?? undefined, status: tab } } }),
    myCourses(client, me, courseId),
  ]).catch(() => null);

  if (!loaded) return <QuestionsLayout><Notice role="alert" text={t("errors.load")} /></QuestionsLayout>;
  const [{ data: list, response }, { courses, taught, own }] = loaded;
  if (response.status === 401) {
    return (
      <QuestionsLayout>
        <Notice text={t("loginPrompt")} link={{ href: "/login", label: t("signIn") }} />
      </QuestionsLayout>
    );
  }
  if (response.status === 404) {
    return (
      <QuestionsLayout>
        <Notice text={t("courseMissing")} link={{ href: "/questions", label: t("allCoursesLink") }} />
      </QuestionsLayout>
    );
  }
  if (!list) return <QuestionsLayout><Notice role="alert" text={t("errors.load")} /></QuestionsLayout>;

  return (
    <QuestionsLayout>
      <h1 className="sr-only">{t("title")}</h1>
      <div className="flex flex-wrap items-center gap-3">
        <CourseFilter courses={courses} courseId={courseId} tab={tab} />
      </div>
      {courseId === null && own === 0 ? (
        <Notice text={t("noCourses")} link={{ href: "/chat", label: t("chooseCourses") }} />
      ) : (
        <>
          <QuestionTabs counts={list.counts} courseId={courseId} tab={tab} />
          {list.items.length === 0 ? (
            <Notice text={t(tab === "open" ? "emptyOpen" : "emptyAnswered")} />
          ) : (
            <ul className="grid gap-4">
              {list.items.map((question) => (
                <li key={question.id}>
                  <QuestionCard question={question} variant="list" showCourse={courseId === null}
                    teaches={taught.has(question.course.id)} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </QuestionsLayout>
  );
}
