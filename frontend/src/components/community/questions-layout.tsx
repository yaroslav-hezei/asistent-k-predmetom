/** The column of the "Otázky komunity" pages: 840px of content, as all list pages. */
export function QuestionsLayout({ children }: { children: React.ReactNode }) {
  return (
    <section className="mx-auto grid w-full max-w-[880px] gap-5 px-4 pt-2 pb-10 sm:px-5 md:pt-4">
      {children}
    </section>
  );
}
