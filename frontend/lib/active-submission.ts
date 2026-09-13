"use client";

import { useSyncExternalStore } from "react";

/**
 * What the floating assistant needs to know, published from anywhere.
 *
 * The assistant is mounted once in the root layout, so it sits outside the
 * filing page's component tree and cannot be handed anything through props. A
 * module-level store is the smallest thing that bridges the two: the filing
 * page publishes an id once a verdict exists, the widget reads it, and
 * everywhere else the value stays null -- which the backend treats as "answer
 * from the RNE texts alone, and claim nothing about documents you have not
 * seen".
 */
export type AssistantState = {
  submissionId: string | null;
  /**
   * Whether the widget is showing. It lives here rather than in the widget's
   * own state so that anything on the page can open it -- the verdict's
   * "understand this result" is the same assistant, not a second one.
   */
  open: boolean;
};

const INITIAL: AssistantState = { submissionId: null, open: false };

let state: AssistantState = INITIAL;
const listeners = new Set<() => void>();

function publish(next: AssistantState): void {
  state = next;
  for (const notify of listeners) notify();
}

export function setActiveSubmission(submissionId: string | null): void {
  if (submissionId === state.submissionId) return;
  publish({ ...state, submissionId });
}

export function openAssistant(): void {
  if (!state.open) publish({ ...state, open: true });
}

export function setAssistantOpen(open: boolean): void {
  if (open !== state.open) publish({ ...state, open });
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useAssistantState(): AssistantState {
  // The snapshot is a stable reference between publishes, which is what
  // useSyncExternalStore requires; the server snapshot is the initial state,
  // since nothing is being filed during a render on the server.
  return useSyncExternalStore(
    subscribe,
    () => state,
    () => INITIAL,
  );
}
