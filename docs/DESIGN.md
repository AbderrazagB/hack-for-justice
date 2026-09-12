# Sahilli — Design System

Design lead notes for the UI overhaul. Written before implementation, then revised
against the constraints (see *Critical review* at the end).

> **Sourcing note.** No RNE portal screenshots exist in this repository or in this
> working session. The palette below is derived from the *described* observations of
> RNE's public portal — deep navy header, white content area, teal/cyan accent, clean
> card layout — not from image files I was able to inspect. If actual screenshots are
> available, the exact navy and teal should be re-sampled from them; the token system
> is structured so that changing two hex values propagates everywhere.

---

## 1. Color

Institutional credibility without cloning a government seal. Navy carries structure,
white carries content, teal is scarce and always means "this is the thing to act on".

### Core tokens

| Token | Hex | Role |
|---|---|---|
| `--navy` | **#0E2747** | Primary structural color. App chrome, officer dashboard header, headings. |
| `--navy-deep` | **#081A31** | Navy pressed/hover state; gradient floor on the dashboard masthead. |
| `--navy-soft` | **#1B3A63** | Navy borders and dividers on dark surfaces. |
| `--teal` | **#15ADA2** | The single accent. Primary action fills, active states, focus rings. |
| `--teal-ink` | **#0B6E68** | Teal for *text on white*. #15ADA2 measures 2.79:1 on white and fails AA; this is 6.10:1. |
| `--teal-wash` | **#E6F6F4** | Teal at low intensity — selected rows, accent chip backgrounds. |

### Neutrals

Not Tailwind's default gray. Every neutral is pulled toward the navy hue (blue cast,
~215° ) so grays sit beside the navy rather than fighting it.

| Token | Hex | Role |
|---|---|---|
| `--canvas` | **#FAFBFC** | Page background. |
| `--surface` | **#FFFFFF** | Cards, panels, table rows. |
| `--ink` | **#16273B** | Body text. Navy-derived, not black. |
| `--ink-muted` | **#5A6E85** | Secondary text, labels, metadata. 4.6:1 on canvas. |
| `--ink-faint` | **#7D8FA2** | Tertiary — timestamps, counts, disabled labels. 3.21:1 on canvas. |
| `--line` | **#DEE5EC** | Default borders. |
| `--line-strong` | **#C2CEDA** | Emphasised borders, table header rules. |

### Status system

One color per status, used identically in the MSME tracker, the officer queue, and the
detail view. Each has an ink (text/icon) and a wash (background) so a badge, a row
accent, and a tracker step all read as the same state.

| Status | Ink | Wash | Icon (lucide) | Meaning |
|---|---|---|---|---|
| `SUBMITTED` | `#5A6E85` | `#EEF1F5` | `Inbox` | Received, not yet checked. |
| `PRE_VALIDATED` | `#0B6E68` | `#E6F6F4` | `ShieldCheck` | Passed Sahilli's checks. |
| `UNDER_INSTITUTIONAL_REVIEW` | `#0E2747` | `#E7ECF3` | `Landmark` | With the registry. |
| `APPROVED` | `#0F7B5A` | `#E5F3ED` | `CircleCheck` | Terminal, accepted. |
| `REJECTED` | `#A5231C` | `#FBEAE8` | `CircleX` | Terminal, refused. |
| `NEEDS_CORRECTION` | `#8F5206` | `#FBF1E3` | `CircleAlert` | Actionable, returns to the applicant. |

Completeness reuses the same three semantics: `COMPLETE` → approved green,
`INCOMPLETE` → rejected red, `NEEDS_REVIEW` → correction amber.

Flag severity: `ERROR` → `#A5231C`, `WARNING` → `#8F5206`, `INFO` → `#0B6E68`.

Green (#0F7B5A) is deliberately blue-leaning so it reads as a sibling of the teal rather
than a second, unrelated accent.

---

## 2. Typography

Two families, clearly separated by role, plus a dedicated Arabic face.

- **Space Grotesk** — headings, figures, and all numeric data (stat values, counts,
  CIN numbers, dates). Geometric with unusual details; gives the product a technical,
  built identity and makes tabular numbers distinctive. Not a neutral default.
- **IBM Plex Sans** — body copy, form labels, table content, buttons. Designed for
  civic and enterprise software, highly readable at small sizes, and institutionally
  credible without being bureaucratic.
- **IBM Plex Sans Arabic** — all Arabic text. Same superfamily as the body face, so the
  French and Arabic lines of a bilingual label share proportions and weight instead of
  clashing. This is the reason for choosing Plex over a generic pairing: the Arabic
  requirement is solved by design, not patched.

### Scale

Set explicitly; no default browser sizes.

| Role | Size / line-height | Family | Weight | Tracking |
|---|---|---|---|---|
| Display | 2.5rem / 1.1 | Grotesk | 600 | -0.02em |
| H1 | 1.875rem / 1.2 | Grotesk | 600 | -0.015em |
| H2 | 1.25rem / 1.3 | Grotesk | 600 | -0.01em |
| H3 | 1rem / 1.4 | Grotesk | 600 | 0 |
| Stat figure | 2.25rem / 1 | Grotesk | 600 | -0.02em, tabular |
| Body | 0.9375rem / 1.6 | Plex | 400 | 0 |
| Label | 0.8125rem / 1.4 | Plex | 500 | 0 |
| Meta | 0.75rem / 1.4 | Plex | 400 | 0 |
| Data / mono | 0.8125rem | Grotesk | 500 | tabular-nums |

No tracked-out all-caps eyebrow labels anywhere.

---

## 3. Layout, per screen

**`/` — entry.** Full-bleed navy field, one display-size statement of what Sahilli does,
and two routes in. The two routes are *not* matching cards: the MSME path is a solid
teal-bordered panel on white; the officer path is a quieter inset on the navy itself.
Asymmetric by intent — most visitors are businesses.

**`/msme` — service selection.** Breaks the equal-grid problem outright. *Modification
Entreprise* is a single wide feature panel across the top: navy left rail carrying the
RNE-M-005 reference, white body with the bilingual title, the five required documents
listed inline, and the primary action. The five unavailable services sit **below, in a
plain bordered list** — one row each, muted, no card, no shadow, no radius echo. They
read as a roadmap, not as five siblings of the live one.

**`/msme/[transactionType]` — the filing flow.** Two columns on desktop, stacked on
mobile. Left: the document checklist as a vertical rail with a connecting line and a
state marker per row, so progress is legible at a glance. Right: a sticky verdict panel
that starts as a quiet instruction and becomes the result. The document rail and the
verdict panel are visually different objects — the rail is structural and borderless,
the panel is a raised, bordered surface with a status-colored top edge.

**`/admin` — officer queue.** Navy masthead spanning the full width carrying the four
figures as a stat band directly on the navy — glanceable, no cards, separated by hairline
rules. Below on white: the filter row, then the queue as a **dense table**, not cards.
Each row carries a 3px left border in its status color, a monospace id, the transaction,
a flag cell, and the status. Zebra-free; hairline row rules only.

**`/admin/[submissionId]` — review.** A dense working screen. Sticky navy sub-header with
the dossier id and the decision actions always reachable. Findings run full-width as a
list with a severity-colored left edge. Below, the per-document inspection is a two-pane
split: original document on the left, extracted fields on the right in a tabular layout
with tabular figures. The decision panel is the only element on the page with a teal
border — it is the one thing the officer is here to do.

---

## 4. Motion

Three React Bits components (installed via `npx shadcn@latest add @react-bits/…`),
each used once, for one orchestrated moment per screen. No hover effects on every card,
no fade-slide-up on every section.

| Component | Where | Why |
|---|---|---|
| `SpotlightCard` | `/msme`, the single *Modification Entreprise* panel | Makes the one live service the only interactive-feeling object on the page. Directly serves the hierarchy goal. |
| `BlurText` | `/msme/[type]`, the verdict headline when the check returns | The one moment that matters to an applicant: the answer arriving. Word-by-word settle, ~500ms, once. |
| `CountUp` | `/admin`, the four masthead figures | Live data announcing itself as live. Runs once on load. |

All three are wrapped in a `Motion` guard that reads `prefers-reduced-motion` and renders
the final state statically when motion is reduced. React Bits ships no reduced-motion
handling of its own, so this is ours.

---

## 5. Principles — what makes this not a template

1. **Scarcity is the system.** Exactly one teal element per screen carries the primary
   action. Everything else is navy, white, or a status color. Templates spread their
   accent everywhere; here, finding the teal tells you what to do next.
2. **Different jobs get different objects.** A stat band, a queue table, and a document
   inspector are not three paddings of one card component. The equal-weight card grid is
   removed on purpose, including for the "coming soon" services, which become a list.
3. **Bilingual is structural, not decorative.** Every status, document label and finding
   carries FR and AR from `rules_engine.py`, set in a matched superfamily, with `dir`
   isolation per string rather than a flipped layout.

---

## 6. Critical review — what this plan got wrong first, and what changed

Reviewed against the brief before implementation. Four things in the first draft were
exactly the defaults the brief rejects:

1. **Tracked-out all-caps eyebrows.** The first draft carried `HACK4JUSTICE 2026` and
   `RÉF. RNE-M-005` as uppercase letterspaced labels above headings — named in the brief
   as an AI-UI tell. *Changed:* the reference is now set as normal-case data type inside
   the feature panel's navy rail, where it functions as a record locator rather than
   decoration. No eyebrow labels anywhere.
2. **`→` appended to every action.** Draft had "Commencer →", "Préparer mon dossier →",
   "Ouvrir le tableau de bord →". *Changed:* removed entirely. Buttons now name the
   action ("Vérifier les pièces", "Enregistrer la décision") and lucide icons carry
   direction only where direction is the actual meaning (back navigation).
3. **Uniform cards with the same soft shadow.** Draft reused one `Card` with
   `rounded-xl border shadow-sm` for services, stats, queue rows and the review panel.
   *Changed:* shadow is now reserved for genuinely floating surfaces (the sticky verdict
   panel). Structural surfaces use borders and background shifts. Radius is tiered: 10px
   for panels, 6px for controls, 0 for table rows and the stat band.
4. **Motion everywhere.** Draft had hover lift on every card plus a staggered reveal on
   every section — the "generic and templated" outcome the brief warns about. *Changed:*
   cut to three components, one moment per screen, each justified in the table above.

Two further changes came from measuring rather than from the tropes list. Every
foreground/background pair in the token table was run through a WCAG contrast
calculation, not eyeballed:

- The first draft used `#15ADA2` for teal text on white. It measures **2.79:1** and
  fails AA, so `--teal-ink` (#0B6E68, **6.10:1**) was added as a separate token. The
  bright teal is now fill-only — it is still used for text on navy, where it measures
  5.38:1 and passes.
- `--ink-faint` was first `#8496A8`, which measures **2.93:1** on the canvas and misses
  the 3:1 floor for incidental text. Darkened to **#7D8FA2** (3.21:1).

Measured results for the final tokens: ink 14.61:1, ink-muted 5.06:1, white-on-navy
15.00:1, approved 5.25:1, rejected 7.35:1, correction 6.22:1, submitted 5.25:1.
