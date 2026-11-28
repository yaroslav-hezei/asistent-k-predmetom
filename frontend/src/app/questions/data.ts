import type { Course, Me } from "@/lib/api/client";
import type { apiWithToken } from "@/lib/api/server";

type Api = ReturnType<typeof apiWithToken>;

/**
 * The courses of "Predmet:": the user's study plan ("Moje predmety") and the courses they teach,
 * by name, plus `extraId` (a course opened by a link) when it is neither. `taught` = the courses
 * the user teaches (answers verified, may hide spam); `own` = how many plan and taught courses.
 */
export async function myCourses(client: Api, me: Me, extraId: string | null) {
  const [plan, taught, extra] = await Promise.all([
    me.study
      ? client.GET("/programs/{program_id}/courses", {
        params: {
          path: { program_id: me.study.program_id },
          query: { year: me.study.year, semester: me.study.semester },
        },
      })
      : null,
    me.role === "vyucujuci" ? client.GET("/teacher/courses") : null,
    extraId ? client.GET("/courses/{course_id}", { params: { path: { course_id: extraId } } }) : null,
  ]);
  const byId = new Map<string, Course>();
  for (const item of plan?.data ?? []) byId.set(item.course.id, item.course);
  const taughtIds = new Set<string>();
  for (const item of taught?.data ?? []) {
    byId.set(item.course.id, item.course);
    taughtIds.add(item.course.id);
  }
  const own = byId.size;
  if (extra?.data) byId.set(extra.data.id, extra.data);
  const courses = [...byId.values()].sort((a, b) => a.name.localeCompare(b.name, "sk"));
  return { courses, taught: taughtIds, own };
}

/** The courses the user teaches (empty for a student). */
export async function taughtCourseIds(client: Api, me: Me) {
  if (me.role !== "vyucujuci") return new Set<string>();
  const { data } = await client.GET("/teacher/courses");
  return new Set((data ?? []).map((item) => item.course.id));
}
