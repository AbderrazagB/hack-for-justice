/**
 * The small slice of Markdown the assistant actually produces.
 *
 * Its answers arrive as Markdown -- numbered lists of required documents,
 * **bold** on the deadline that matters -- and were being printed raw, so a
 * reader saw literal asterisks and, in Arabic, a bidi mess where "1." at the
 * start of a line lands wherever the algorithm puts it rather than in a list
 * marker. This turns them into real elements: an `ol` numbers itself, and its
 * markers follow the direction of the text.
 *
 * Deliberately not a Markdown library. The input is one constrained generator
 * under a prompt that caps it at 200 words, the subset below covers what it
 * emits, and building React nodes rather than HTML means there is no
 * dangerouslySetInnerHTML anywhere near model output.
 */
import type { ReactNode } from "react";

type Block =
  | { kind: "heading"; level: number; text: string }
  | { kind: "bullets"; items: string[] }
  | { kind: "numbers"; items: string[]; start: number }
  | { kind: "paragraph"; text: string };

const BULLET = /^\s*[-*+]\s+(.*)$/;
const NUMBER = /^\s*(\d+)[.)]\s+(.*)$/;
const HEADING = /^\s*(#{1,6})\s+(.*)$/;

export function parseBlocks(source: string): Block[] {
  const blocks: Block[] = [];
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  let paragraph: string[] = [];

  const flush = () => {
    const text = paragraph.join(" ").trim();
    if (text) blocks.push({ kind: "paragraph", text });
    paragraph = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (!line.trim()) {
      flush();
      continue;
    }

    const heading = HEADING.exec(line);
    if (heading) {
      flush();
      blocks.push({ kind: "heading", level: heading[1].length, text: heading[2] });
      continue;
    }

    if (BULLET.test(line) || NUMBER.test(line)) {
      flush();
      const numbered = NUMBER.test(line);
      const items: string[] = [];
      const start = numbered ? Number(NUMBER.exec(line)![1]) : 1;

      // Consume the run, including lines that wrap under an item.
      while (i < lines.length) {
        const current = lines[i];
        const match = numbered ? NUMBER.exec(current) : BULLET.exec(current);
        if (match) {
          items.push(numbered ? match[2] : match[1]);
          i++;
          continue;
        }

        // A marker of the *other* kind ends this run rather than being folded
        // into the item above it. Swallowing it printed the sub-bullets of a
        // numbered item as literal dashes mid-sentence:
        //   "1. Dépôt des états financiers : - Les états ... - Si applicable :"
        const otherMarker = numbered ? BULLET.test(current) : NUMBER.test(current);
        if (otherMarker || HEADING.test(current) || !current.trim() || !items.length) {
          break;
        }

        items[items.length - 1] += ` ${current.trim()}`;
        i++;
      }
      i--;

      blocks.push(
        numbered ? { kind: "numbers", items, start } : { kind: "bullets", items },
      );
      continue;
    }

    paragraph.push(line.trim());
  }

  flush();
  return blocks;
}

// **bold** before *italic*, so the opening ** is never read as an italic mark.
const INLINE = /(\*\*[^*]+?\*\*|__[^_]+?__|`[^`]+?`|\*[^*\n]+?\*)/g;

function inline(text: string, keyPrefix: string): ReactNode[] {
  return text.split(INLINE).filter(Boolean).map((piece, index) => {
    const key = `${keyPrefix}-${index}`;
    if (
      (piece.startsWith("**") && piece.endsWith("**")) ||
      (piece.startsWith("__") && piece.endsWith("__"))
    ) {
      return (
        <strong key={key} className="font-semibold text-[var(--ink)]">
          {piece.slice(2, -2)}
        </strong>
      );
    }
    if (piece.startsWith("`") && piece.endsWith("`")) {
      return (
        <code
          key={key}
          className="t-data rounded bg-[var(--canvas)] px-1 py-0.5 text-[0.9em]"
        >
          {piece.slice(1, -1)}
        </code>
      );
    }
    if (piece.startsWith("*") && piece.endsWith("*") && piece.length > 2) {
      return <em key={key}>{piece.slice(1, -1)}</em>;
    }
    return <span key={key}>{piece}</span>;
  });
}

export function Markdown({
  text,
  rtl = false,
  className = "",
}: {
  text: string;
  rtl?: boolean;
  className?: string;
}) {
  const blocks = parseBlocks(text);

  return (
    // dir carries to the list markers: an Arabic `ol` numbers down its right
    // edge, and ps-* is padding-inline-start, so the indent follows too.
    <div
      dir={rtl ? "rtl" : "ltr"}
      className={`space-y-2.5 ${rtl ? "ar" : ""} ${className}`}
    >
      {blocks.map((block, index) => {
        const key = `b${index}`;
        if (block.kind === "heading") {
          return (
            <p key={key} className="t-label pt-1 text-[var(--navy)]">
              {inline(block.text, key)}
            </p>
          );
        }
        if (block.kind === "bullets") {
          return (
            <ul key={key} className="list-disc space-y-1 ps-5 marker:text-[var(--ink-faint)]">
              {block.items.map((item, position) => (
                <li key={position}>{inline(item, `${key}-${position}`)}</li>
              ))}
            </ul>
          );
        }
        if (block.kind === "numbers") {
          return (
            <ol
              key={key}
              start={block.start}
              className="list-decimal space-y-1 ps-5 marker:text-[var(--ink-faint)]"
            >
              {block.items.map((item, position) => (
                <li key={position}>{inline(item, `${key}-${position}`)}</li>
              ))}
            </ol>
          );
        }
        return <p key={key}>{inline(block.text, key)}</p>;
      })}
    </div>
  );
}
