import type { components } from "./schema";

/** Types of "Otázky komunity" (generated from the backend's Pydantic models). */
export type QuestionSummary = components["schemas"]["QuestionSummary"];
export type QuestionList = components["schemas"]["QuestionList"];
export type QuestionDetail = components["schemas"]["QuestionDetail"];
export type CommunityAnswer = components["schemas"]["CommunityAnswer"];
export type Author = components["schemas"]["Author"];
export type QuestionStatus = QuestionSummary["status"];
