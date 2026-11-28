import { CoursePicker } from "@/components/course-picker";
import type { Course } from "@/lib/api/client";
import { getChatHistory } from "@/lib/chat-history";

export default async function ChatPage() {
  const courses = new Map<string, Course>();
  for (const { course } of await getChatHistory()) {
    if (!courses.has(course.id)) courses.set(course.id, course);
    if (courses.size === 4) break;
  }
  return <CoursePicker recentCourses={[...courses.values()]} />;
}
