import type { QuestionStatus } from "@/lib/api/community";

/** The URL of one tab of "Otázky komunity": all my courses (`courseId` null) or one course. */
export function questionsHref(courseId: string | null, tab: QuestionStatus) {
  const params = new URLSearchParams();
  if (courseId) params.set("course", courseId);
  if (tab === "answered") params.set("tab", "answered");
  const query = params.toString();
  return query ? `/questions?${query}` : "/questions";
}
