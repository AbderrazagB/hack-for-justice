"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * Reduced-motion guard for the React Bits components.
 *
 * React Bits ships no `prefers-reduced-motion` handling of its own, so every
 * animated component is rendered through this: when the user has asked for
 * reduced motion we render the final, settled state and never mount the
 * animation at all.
 *
 * Implemented with `useSyncExternalStore` because a media query is exactly an
 * external store — it subscribes without the cascading re-render that reading
 * it in an effect would cause. The server snapshot is `true`, so server-rendered
 * HTML is always the static version and the animated one mounts only once the
 * client has read the real preference.
 */

const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(onChange: () => void): () => void {
  const query = window.matchMedia(QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

export function useReducedMotion(): boolean {
  const getSnapshot = useCallback(() => window.matchMedia(QUERY).matches, []);
  const getServerSnapshot = useCallback(() => true, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export function Animated({
  children,
  fallback,
}: {
  children: React.ReactNode;
  fallback: React.ReactNode;
}) {
  return useReducedMotion() ? <>{fallback}</> : <>{children}</>;
}
