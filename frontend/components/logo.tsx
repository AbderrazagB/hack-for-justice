import Image from "next/image";
import Link from "next/link";

/**
 * The Sahilli mark.
 *
 * The mark is a transparent PNG, so it sits directly on whatever surface it is
 * placed on — no tile, no plate, no ring. It reads on navy and on white alike.
 */
export function Logo({
  size = "md",
  tone = "light",
  href = "/",
}: {
  size?: "sm" | "md" | "lg" | "xl";
  tone?: "light" | "dark";
  href?: string | null;
}) {
  const scale = {
    sm: { mark: "size-9", px: "36px", name: "text-[1.25rem]", ar: "text-[1rem]", gap: "gap-2.5" },
    md: { mark: "size-12", px: "48px", name: "text-[1.625rem]", ar: "text-[1.3125rem]", gap: "gap-3" },
    lg: { mark: "size-16", px: "64px", name: "text-[2.125rem]", ar: "text-[1.75rem]", gap: "gap-3.5" },
    xl: { mark: "size-20", px: "80px", name: "text-[2.75rem]", ar: "text-[2.25rem]", gap: "gap-4" },
  }[size];

  const nameColor = tone === "dark" ? "text-white" : "text-[var(--navy)]";
  const arColor = tone === "dark" ? "text-white/65" : "text-[var(--ink-muted)]";

  const lockup = (
    <span className={`inline-flex items-center ${scale.gap}`}>
      <Image
        src="/brand/sahilli-mark.png"
        alt=""
        aria-hidden
        width={1254}
        height={1254}
        sizes={scale.px}
        priority
        className={`${scale.mark} shrink-0 object-contain`}
      />

      <span className="flex items-baseline gap-2.5">
        <span
          className={`font-[family-name:var(--font-space-grotesk)] ${scale.name} leading-none font-bold tracking-[-0.025em] ${nameColor}`}
        >
          Sahilli
        </span>
        <span className={`ar ${scale.ar} leading-none font-medium ${arColor}`}>
          سهّلي
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
