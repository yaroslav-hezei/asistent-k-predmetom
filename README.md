# Asistent k predmetom — AI assistant for course information

A web app that answers students' questions about how a course really runs — grading, deadlines, attendance —
**before it starts**. Answers come from the official course information sheets (MAIS) and from answers of other
students and teachers, always with a quote, source, date and author. When the assistant does not know,
it says so ("Neviem"), the question goes to the community, and the first answer immediately becomes part
of the assistant's knowledge. Teachers can add verified answers.

Semester project for *Hospodárska informatika v praxi* (HIP 2026–2027), TUKE FEI.
Team: Yaroslav Hezei, Bohdan Muzhyla, Mykola Parlach.

**Status:** MVP in development.

## Stack

| Part | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI, Pydantic |
| Data & auth | Supabase (Postgres + pgvector, Auth) |
| AI | Gemini embeddings + Gemini Flash-Lite, retrieval-augmented generation (own implementation) |
| Infra | Docker, Vercel, Google Cloud Run, GitHub Actions |

## Repository layout (planned)

```
frontend/              Next.js app
backend/               FastAPI app (API, RAG)
supabase/migrations/   database schema
scripts/               scraper, seed data, evaluation, workspace setup
docs/design/           UI reference (hi-fi prototype) and design notes
```

## Contributing

Team setup, tasks and tools: see [CONTRIBUTING.md](CONTRIBUTING.md).
