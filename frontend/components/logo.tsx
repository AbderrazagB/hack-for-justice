import Image from "next/image";
import Link from "next/link";

const LIGHT_OUTLINE_FILTER = {
  thin: "drop-shadow(1px 0 0 var(--navy)) drop-shadow(-1px 0 0 var(--navy)) drop-shadow(0 1px 0 var(--navy)) drop-shadow(0 -1px 0 var(--navy))",
  thick:
    "drop-shadow(1.5px 0 0 var(--navy)) drop-shadow(-1.5px 0 0 var(--navy)) drop-shadow(0 1.5px 0 var(--navy)) drop-shadow(0 -1.5px 0 var(--navy))",
} as const;

/**
 * The Sahilli wordmark.
 *
 * Separate transparent assets keep the lettering crisp and intentional on both
 * light and dark surfaces without adding a tile, plate or filter.
 */
export function Logo({
  size = "md",
  tone = "light",
  lightOutline = "thick",
  href = "/",
}: {
  size?: "sm" | "md" | "lg" | "xl";
  tone?: "light" | "dark";
  lightOutline?: keyof typeof LIGHT_OUTLINE_FILTER;
  href?: string | null;
}) {
  const scale = {
    sm: { className: "h-7", sizes: "134px" },
    md: { className: "h-8", sizes: "154px" },
    lg: { className: "h-10", sizes: "192px" },
    xl: { className: "h-12 sm:h-14", sizes: "270px" },
  }[size];

  const variant =
    tone === "dark"
      ? {
          src: "/brand/sahilli-wordmark-dark.png",
          width: 1749,
          height: 368,
        }
      : {
          src: "/brand/sahilli-wordmark-light.png",
          width: 1749,
          height: 368,
        };

  const lockup = (
    <Image
      src={variant.src}
      alt="Sahilli — سهّلي"
      width={variant.width}
      height={variant.height}
      sizes={scale.sizes}
      priority
      unoptimized={tone === "light"}
      className={`${scale.className} w-auto shrink-0 object-contain`}
      style={
        tone === "light"
          ? {
              filter: LIGHT_OUTLINE_FILTER[lightOutline],
            }
          : undefined
      }
    />
  );

  if (!href) return lockup;

  return (
    <Link href={href} className="inline-flex rounded-[var(--r-control)]">
      {lockup}
    </Link>
  );
}
