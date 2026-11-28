import { ArrowLeft } from "lucide-react";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { AnswerItem } from "@/components/community/answer-item";
import { Notice } from "@/components/community/notice";
import { QuestionCard } from "@/components/community/question-card";
import { QuestionsLayout } from "@/components/community/questions-layout";
import { serverApi } from "@/lib/api/server";
import { getMe } from "@/lib/auth/me";
import { taughtCourseIds } from "../data";

export default async function QuestionPage({ params }: { params: Promise<{ questionId: string }> }) {
  const t = await getTranslations("questions");
  const me = await getMe();
  const login = <Notice text={t("loginPrompt")} link={{ href: "/login", label: t("signIn") }} />;
  if (!me) return <QuestionsLayout>{login}</QuestionsLayout>;
  const { questionId } = await params;
  const client = await serverApi();
  const loaded = await Promise.all([
    client.GET("/questions/{question_id}", { params: { path: { question_id: questionId } } }),
    taughtCourseIds(client, me),
  ]).catch(() => null);

  if (!loaded) return <QuestionsLayout><Notice role="alert" text={t("errors.load")} /></QuestionsLayout>;
  const [{ data: question, response }, taught] = loaded;
  if (response.status === 401) return <QuestionsLayout>{login}</QuestionsLayout>;
  if (response.status === 404 || response.status === 422) {
    return (
      <QuestionsLayout>
        <Notice text={t("questionMissing")} link={{ href: "/questions", label: t("back") }} />
      </QuestionsLayout>
    );
  }
  if (!question) return <QuestionsLayout><Notice role="alert" text={t("errors.load")} /></QuestionsLayout>;
  const teaches = taught.has(question.course.id);

  return (
    <QuestionsLayout>
      <Link href={`/questions?course=${encodeURIComponent(question.course.id)}`}
        className="inline-flex min-h-11 items-center gap-2 justify-self-start font-medium text-fei-dark hover:underline">
        <ArrowLeft size={16} aria-hidden="true" />
        {t("back")}
      </Link>
      <QuestionCard question={question} variant="detail" showCourse teaches={teaches} />
      <section aria-labelledby="answers-title" className="grid gap-3">
        <h2 id="answers-title" className="flex items-center gap-2 font-semibold">
          {t("answersTitle")}
          <span className="rounded-full bg-nav-active px-2 text-[13px] text-muted-foreground">{question.answers.length}</span>
        </h2>
        {question.answers.length === 0 ? (
          <p className="text-muted-foreground">{t("noAnswers")}</p>
        ) : (
          <ul className="grid gap-3">
            {question.answers.map((answer) => (
              <AnswerItem key={answer.id} answer={answer} teaches={teaches} />
            ))}
          </ul>
        )}
      </section>
    </QuestionsLayout>
  );
}
