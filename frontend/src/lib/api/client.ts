import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type Program = components["schemas"]["Program"];
export type Course = components["schemas"]["CourseSummary"];
export type PlanCourse = components["schemas"]["ProgramCourse"];
export type Semester = PlanCourse["semester"];

export const api = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  cache: "no-store",
});

