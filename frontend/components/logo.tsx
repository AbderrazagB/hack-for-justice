import Link from "next/link";
import Image from "next/image";

/**
 * The Sahilli mark.
 *
 * The generated mark combines a document, check and Arabic-inspired curve.
 * Its transparent master is kept large and rendered through next/image so the
 * same crisp lockup works across public, applicant and officer experiences.
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
    sm: { tile: "size-8", name: "text-[1.125rem]", ar: "text-[0.9375rem]" },
    md: { tile: "size-10", name: "text-[1.375rem]", ar: "text-[1.125rem]" },
    lg: { tile: "size-12", name: "text-[1.75rem]", ar: "text-[1.375rem]" },
  }[size];

  const nameColor = tone === "dark" ? "text-white" : "text-[var(--navy)]";
  const arColor = tone === "dark" ? "text-white/60" : "text-[var(--ink-muted)]";

  const lockup = (
    <span className="inline-flex items-center gap-2.5">
      <span
        aria-hidden
        className={`${scale.tile} relative flex shrink-0 items-center justify-center overflow-hidden rounded-[11px] bg-white shadow-[0_8px_24px_-12px_rgba(8,26,49,0.55)] ring-1 ${
          tone === "dark" ? "ring-white/20" : "ring-[var(--line)]"
        }`}
      >
        <Image
          src="/brand/sahilli-mark.png"
          alt=""
          width={1254}
          height={1254}
          sizes="48px"
          className="h-[86%] w-[86%] object-contain"
        />
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
