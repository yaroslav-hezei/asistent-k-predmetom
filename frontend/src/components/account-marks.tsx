import { BookOpen } from "lucide-react";

export function BrandMark() {
  return (
    <span aria-hidden="true" className="grid size-[30px] shrink-0 place-items-center rounded-[9px] bg-fei text-on-fei">
      <BookOpen size={17} />
    </span>
  );
}

export function Avatar({ nickname, compact = false }: { nickname: string; compact?: boolean }) {
  const [first, second] = nickname.trim().split(/\s+/);
  const digits = nickname.trim().match(/\d+$/)?.[0];
  const letters = Array.from(first);
  const initials = digits || second
    ? (letters[0] ?? "") + (digits ?? Array.from(second)[0])
    : letters.slice(0, 2).join("");

  return (
    <span aria-hidden="true" className={`grid shrink-0 place-items-center rounded-full bg-avatar text-[13px] font-semibold text-on-avatar ${compact ? "size-8" : "size-[34px]"}`}>
      {initials.toUpperCase()}
    </span>
  );
}
