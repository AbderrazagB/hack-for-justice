import Link from "next/link";

/**
 * The Sahilli mark.
 *
 * Built from type and shape only — no image file, no emblem. A navy tile holds
 * the Arabic letter س (the first letter of سهّلي) with a teal bar beneath it,
 * echoing the underline that separates the two scripts in the wordmark. The
 * tile scales with the wordmark so the lockup holds together at any size.
 */
export function Logo({
  size = "md",
  tone = "light",
  href = "/",
}: {
  size?: "sm" | "md" | "lg";
  tone?: "light" | "dark";
  href?: string | null;
}) {
  const scale = {
    sm: { tile: "size-8", glyph: "text-[1.125rem]", name: "text-[1.125rem]", ar: "text-[0.9375rem]" },
    md: { tile: "size-10", glyph: "text-[1.375rem]", name: "text-[1.375rem]", ar: "text-[1.125rem]" },
    lg: { tile: "size-12", glyph: "text-[1.625rem]", name: "text-[1.75rem]", ar: "text-[1.375rem]" },
  }[size];

  const nameColor = tone === "dark" ? "text-white" : "text-[var(--navy)]";
  const arColor = tone === "dark" ? "text-white/60" : "text-[var(--ink-muted)]";

  const lockup = (
    <span className="inline-flex items-center gap-2.5">
      <span
        aria-hidden
        className={`${scale.tile} relative flex shrink-0 items-center justify-center overflow-hidden rounded-[10px] bg-[var(--navy)]`}
      >
        <span
          className={`ar ${scale.glyph} font-semibold leading-none text-white`}
          style={{ marginBottom: "0.12em" }}
        >
          س
        </span>
        <span className="absolute inset-x-1.5 bottom-1.5 h-[2px] rounded-full bg-[var(--teal)]" />
      </span>

      <span className="flex flex-col leading-none">
        <span className="flex items-baseline gap-2">
          <span
            className={`font-[family-name:var(--font-space-grotesk)] ${scale.name} font-bold tracking-[-0.02em] ${nameColor}`}
          >
            Sahilli
          </span>
          <span className={`ar ${scale.ar} font-medium ${arColor}`}>سهّلي</span>
        </span>
      </span>
    </span>
  );

  if (!href) return lockup;

  return (
    <Link href={href} className="inline-flex rounded-[var(--r-control)]">
      {lockup}
    </Link>
  );
}
