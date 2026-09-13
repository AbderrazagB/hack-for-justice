"use client";

import { LogIn, LogOut } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { Logo } from "@/components/logo";
import { currentUser, logout } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

/**
 * Portal chrome for the public entry. Carries Sahilli's own wordmark only —
 * no state emblem, no flag, no RNE logo.
 */
export function PortalBar({ immersive = false }: { immersive?: boolean }) {
  const router = useRouter();
  // null = nobody signed in; undefined = not resolved yet, so the bar does not
  // flash "Se connecter" at someone who is already signed in.
  const [user, setUser] = useState<AuthUser | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    currentUser()
      .then((resolved) => live && setUser(resolved))
      .catch(() => live && setUser(null));
    return () => {
      live = false;
    };
  }, []);

  async function signOut() {
    try {
      await logout();
    } finally {
      setUser(null);
      router.push("/login");
      router.refresh();
    }
  }

  const linkClass = immersive
    ? "text-white/70 hover:bg-white/8 hover:text-white"
    : "text-[var(--ink-muted)] hover:bg-[var(--canvas)] hover:text-[var(--navy)]";

  return (
    <header
      className={`sticky top-0 z-40 border-b backdrop-blur-xl ${
        immersive
          ? "border-white/10 bg-[var(--navy)]/92"
          : "border-[var(--line)] bg-[var(--surface)]/92"
      }`}
    >
      <nav className="mx-auto flex max-w-[1400px] flex-nowrap items-center justify-between gap-2 px-4 py-4 sm:gap-3 sm:px-8">
        <Logo size="lg" tone={immersive ? "dark" : "light"} />
        <div className="flex items-center gap-1">
          <Link
            href="/msme"
            className={`rounded-[var(--r-control)] px-2 py-1.5 text-[0.8125rem] font-medium transition-colors sm:px-3 sm:text-[0.875rem] ${linkClass}`}
          >
            Services
          </Link>
          <Link
            href="/admin"
            className={`rounded-[var(--r-control)] px-2 py-1.5 text-[0.8125rem] font-medium whitespace-nowrap transition-colors sm:px-3 sm:text-[0.875rem] ${linkClass}`}
          >
            Espace agent
          </Link>
          {user === undefined ? (
            <span className="ml-1 h-8 w-28 rounded-full bg-[var(--line)]/60" aria-hidden />
          ) : user ? (
            <>
              <span
                className={`ml-1 hidden max-w-[11rem] truncate text-[0.8125rem] sm:inline ${
                  immersive ? "text-white/70" : "text-[var(--ink-muted)]"
                }`}
                title={user.email}
              >
                {user.full_name}
              </span>
              <button
                type="button"
                onClick={signOut}
                className={`ml-1 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[0.8125rem] font-medium whitespace-nowrap transition-colors sm:px-4 sm:text-[0.875rem] ${
                  immersive
                    ? "border border-white/25 text-white hover:bg-white/10"
                    : "border border-[var(--line-strong)] text-[var(--navy)] hover:bg-[var(--canvas)]"
                }`}
              >
                <LogOut size={15} strokeWidth={2} aria-hidden />
                Se déconnecter
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className={`ml-1 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[0.8125rem] font-medium whitespace-nowrap transition-colors sm:px-4 sm:text-[0.875rem] ${
                immersive
                  ? "border border-white/25 text-white hover:bg-white/10"
                  : "border border-[var(--line-strong)] text-[var(--navy)] hover:bg-[var(--canvas)]"
              }`}
            >
              <LogIn size={15} strokeWidth={2} aria-hidden />
              Se connecter
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}

/** Navy chrome, used for the officer workspace. */
export function AdminBar({ trailing }: { trailing?: ReactNode }) {
  return (
    <header className="on-navy sticky top-0 z-40 bg-[var(--navy)]">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-8">
        <Logo size="md" tone="dark" />
        <div className="flex items-center gap-3">
          <span className="rounded-[var(--r-control)] border border-white/15 px-2.5 py-1 text-[0.75rem] font-medium text-white/75">
            Espace agent
          </span>
          {trailing}
        </div>
      </div>
    </header>
  );
}
