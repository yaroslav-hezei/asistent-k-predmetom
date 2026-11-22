// Keep these public demo accounts in sync with backend/scripts/test_users.json.
export const demoAccounts = [
  { email: "student01@example.com", nickname: "student01", role: "student", year: 1 },
  { email: "student02@example.com", nickname: "student02", role: "student", year: 1 },
  { email: "student03@example.com", nickname: "student03", role: "student", year: 1 },
  { email: "student04@example.com", nickname: "student04", role: "student", year: 2 },
  { email: "student05@example.com", nickname: "student05", role: "student", year: 2 },
  { email: "student06@example.com", nickname: "student06", role: "student", year: 2 },
  { email: "student07@example.com", nickname: "student07", role: "student", year: 3 },
  { email: "student08@example.com", nickname: "student08", role: "student", year: 3 },
  { email: "student09@example.com", nickname: "student09", role: "student", year: 3 },
  { email: "student10@example.com", nickname: "student10", role: "student", year: 3 },
  { email: "vyucujuci01@example.com", nickname: "vyucujuci01", role: "vyucujuci", year: null },
  { email: "vyucujuci02@example.com", nickname: "vyucujuci02", role: "vyucujuci", year: null },
  { email: "vyucujuci03@example.com", nickname: "vyucujuci03", role: "vyucujuci", year: null },
] as const;

export const demoPasswords = {
  student: "hip-student-demo",
  vyucujuci: "hip-vyucujuci-demo",
};
