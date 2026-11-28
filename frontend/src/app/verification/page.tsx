import { getTranslations } from "next-intl/server";
import { Notice } from "@/components/community/notice";
import { QuestionsLayout } from "@/components/community/questions-layout";
import { AnswerToVerify } from "@/components/verification/answer-to-verify";
import { CourseSelect } from "@/components/verification/course-select";
import { NoteEditor } from "@/components/verification/note-editor";
import { serverApi } from "@/lib/api/server";
import { getMe } from "@/lib/auth/me";

export default async function VerificationPage({ searchParams }: {
  searchParams: Promise<{ course?: string | string[] }>;
}) {
  const t = await getTranslations("verification");
  const me = await getMe();
  const page = (content: React.ReactNode) => (
    <QuestionsLayout>
      <h1 className="text-xl font-semibold">{t("title")}</h1>
      {content}
    </QuestionsLayout>
  );
  const login = <Notice text={t("loginPrompt")} link={{ href: "/login", label: t("signIn") }} />;
  if (!me) return page(login);
  if (me.role !== "vyucujuci") return page(<Notice text={t("teachersOnly")} />);

  const client = await serverApi();
  const courses = await client.GET("/teacher/courses").catch(() => null);
  if (courses?.response.status === 401) return page(login);
  if (!courses?.data) return page(<Notice role="alert" text={t("error")} />);
  if (courses.data.length === 0) return page(<Notice text={t("noCourses")} />);

  // the course from the link, else the first one with answers waiting, else the first one
  const { course } = await searchParams;
  const courseId = typeof course === "string" && course ? course
    : (courses.data.find((item) => item.unverified_answers > 0) ?? courses.data[0]).course.id;
  const screen = await client.GET("/teacher/courses/{course_id}", {
    params: { path: { course_id: courseId } },
  }).catch(() => null);
  if (screen?.response.status === 401) return page(login);
  if (screen?.response.status === 403 || screen?.response.status === 404) {
    return page(<Notice text={t("notYourCourse")} link={{ href: "/verification", label: t("back") }} />);
  }
  if (!screen?.data) return page(<Notice role="alert" text={t("error")} />);
  const { note, answers } = screen.data;

  return page(
    <>
      <div className="flex flex-wrap items-center gap-3">
        <CourseSelect courses={courses.data} courseId={courseId} />
      </div>
      <NoteEditor key={courseId} courseId={courseId} note={note} />
      <section aria-labelledby="to-verify" className="grid gap-3">
        <h2 id="to-verify" className="flex items-center gap-2 font-semibold">
          {t("answersTitle")}
          <span className="rounded-full bg-nav-active px-2 text-[13px] text-muted-foreground">{answers.length}</span>
        </h2>
        {answers.length === 0 ? (
          <Notice text={t("noAnswers")} />
        ) : (
          <ul className="grid gap-4">
            {answers.map((answer) => <li key={answer.id}><AnswerToVerify answer={answer} /></li>)}
          </ul>
        )}
      </section>
    </>,
  );
}
