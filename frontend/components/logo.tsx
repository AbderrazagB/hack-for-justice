import Image from "next/image";
import Link from "next/link";

/**
 * The Sahilli wordmark.
 *
 * Separate transparent assets keep the lettering crisp and intentional on both
 * light and dark surfaces without adding a tile, plate or filter.
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
          width: 1980,
          height: 412,
        };

  const lockup = (
    <Image
      src={variant.src}
      alt="Sahilli — سهّلي"
      width={variant.width}
      height={variant.height}
      sizes={scale.sizes}
      priority
      className={`${scale.className} w-auto shrink-0 object-contain`}
    />
  );

  if (!href) return lockup;

  return (
    <Link href={href} className="inline-flex rounded-[var(--r-control)]">
      {lockup}
    </Link>
  );
}
