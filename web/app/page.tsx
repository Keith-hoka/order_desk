"use client";

import { useEffect, useState } from "react";
import { fetchExceptions, submitReview } from "@/lib/api";
import type { FieldFlag, ReviewItem, ReviewStatus } from "@/lib/types";

type ReasonKind = "reply" | "band" | "violation";

function reasonFor(item: ReviewItem): { kind: ReasonKind; label: string } {
  if (item.violations.length > 0) {
    return { kind: "violation", label: item.violations[0] };
  }
  if (item.asks.length > 0) {
    const isReply = item.asks[0].toLowerCase().includes("reply");
    return {
      kind: isReply ? "reply" : "violation",
      label: item.asks[0],
    };
  }
  const bandCount = item.field_flags.filter((f) => f.in_band).length;
  return {
    kind: "band",
    label: `${bandCount} field${bandCount === 1 ? "" : "s"} — model moderately confident`,
  };
}

const KIND_STYLE: Record<ReasonKind, { dot: string; bg: string; text: string }> = {
  reply: { dot: "bg-amber", bg: "bg-amber-bg", text: "text-amber" },
  band: { dot: "bg-ship", bg: "bg-ship-bg", text: "text-ship" },
  violation: { dot: "bg-brick", bg: "bg-brick-bg", text: "text-brick" },
};

export default function Page() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExceptions()
      .then((data) => {
        setItems(data);
        if (data.length > 0) setSelectedId(data[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const selected = items.find((it) => it.id === selectedId) ?? null;
  const flaggedCount = items.filter(
    (it) => it.priority > 0
  ).length;

  async function handleReview(action: ReviewStatus) {
    if (!selected) return;
    const updated = await submitReview(selected.id, action);
    setItems((prev) => prev.map((it) => (it.id === updated.id ? updated : it)));
  }

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center text-ink-soft">
        <p className="font-mono text-sm">Loading review queue…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <div className="max-w-md text-center">
          <p className="mb-2 text-ink">Couldn&apos;t reach the review service.</p>
          <p className="font-mono text-sm text-ink-soft">{error}</p>
          <p className="mt-4 text-sm text-ink-faint">
            Start the API and set NEXT_PUBLIC_API_BASE and NEXT_PUBLIC_API_TOKEN.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <header className="mb-8 flex items-baseline justify-between border-b border-line pb-5">
        <div>
          <h1 className="text-xl font-medium text-ink">Exception review</h1>
          <p className="mt-0.5 text-sm text-ink-soft">
            Extracted orders that need a human before they reach the ERP
          </p>
        </div>
        <p className="font-mono text-sm text-ink-faint">
          {flaggedCount} flagged · {items.length - flaggedCount} clean
        </p>
      </header>

      <div className="grid grid-cols-[260px_minmax(0,1fr)] gap-8">
        <QueueList items={items} selectedId={selectedId} onSelect={setSelectedId} />
        {selected ? (
          <Detail item={selected} onReview={handleReview} />
        ) : (
          <div className="grid place-items-center text-ink-faint">
            <p>Queue is empty.</p>
          </div>
        )}
      </div>
    </main>
  );
}

function QueueList({
  items,
  selectedId,
  onSelect,
}: {
  items: ReviewItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <nav className="flex flex-col gap-1 border-r border-line pr-6">
      {items.map((item) => {
        const reason = reasonFor(item);
        const style = KIND_STYLE[reason.kind];
        const on = item.id === selectedId;
        const reviewed = item.status !== "pending";
        return (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className={`flex flex-col gap-1.5 rounded-lg border px-2.5 py-2 text-left transition ${
              on
                ? "border-line bg-surface"
                : "border-transparent hover:bg-line-soft"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`h-1.5 w-1.5 flex-none rounded-full ${style.dot}`} />
              <span className="font-mono text-xs text-ink">{item.id}</span>
              {reviewed && (
                <span className="font-mono text-[10px] uppercase text-sage">
                  {item.status}
                </span>
              )}
              <span className="ml-auto font-mono text-[11px] text-ink-faint">
                {item.priority.toFixed(1)}
              </span>
            </div>
            <span className="truncate text-xs text-ink-soft">{item.subject}</span>
          </button>
        );
      })}
    </nav>
  );
}

function Detail({
  item,
  onReview,
}: {
  item: ReviewItem;
  onReview: (action: ReviewStatus) => void;
}) {
  const reason = reasonFor(item);
  const style = KIND_STYLE[reason.kind];
  const ex = item.extraction;
  const flagMap = new Map(item.field_flags.map((f) => [f.path, f]));

  return (
    <section className="pl-1">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-mono text-xs text-ink-faint">{item.id}</span>
        <span className="ml-auto text-xs text-ink-faint">
          priority {item.priority.toFixed(1)}
        </span>
      </div>
      <h2 className="mb-4 text-lg font-medium leading-snug text-ink">
        {item.subject}
      </h2>

      <div className={`mb-5 flex items-start gap-2.5 rounded-lg px-3 py-2.5 ${style.bg}`}>
        <span className={`mt-1.5 h-1.5 w-1.5 flex-none rounded-full ${style.dot}`} />
        <span className={`text-sm leading-relaxed ${style.text}`}>{reason.label}</span>
      </div>

      <p className="mb-1 text-[11px] uppercase tracking-wide text-ink-faint">Email</p>
      <p className="mb-6 whitespace-pre-wrap rounded-lg bg-surface px-3 py-2.5 text-sm leading-relaxed text-ink-soft">
        {item.body}
      </p>

      <p className="mb-2 text-[11px] uppercase tracking-wide text-ink-faint">
        Extracted order
      </p>
      {ex ? (
        <>
          <table className="mb-3 w-full border-collapse">
            <tbody>
              <FieldRow label="PO number" value={ex.customer_po_text} flag={flagMap.get("customer_po_text")} />
              <FieldRow label="Delivery address" value={ex.delivery_address_text} flag={flagMap.get("delivery_address_text")} />
              <FieldRow label="Buyer" value={ex.buyer_name_text} flag={flagMap.get("buyer_name_text")} />
              <FieldRow label="Requested date" value={ex.requested_date_text} flag={flagMap.get("requested_date_text")} />
            </tbody>
          </table>
          {ex.line_items.length > 0 && (
            <>
              <p className="mb-1 mt-4 text-[11px] text-ink-faint">Line items</p>
              {ex.line_items.map((li, i) => {
                const pf = flagMap.get(`line_items.${i}.product_text`);
                const qty =
                  li.quantity !== null
                    ? `${li.quantity} ${li.unit_text ?? ""}`.trim()
                    : null;
                return (
                  <div
                    key={i}
                    className="flex items-baseline justify-between border-b border-line py-2"
                  >
                    <span className="text-sm text-ink">
                      {li.product_text}
                      {pf?.in_band && <ConfBadge value={pf.raw_confidence} />}
                    </span>
                    <span className="font-mono text-xs text-ink-soft">
                      {qty ?? <span className="italic text-ink-faint">qty not found</span>}
                    </span>
                  </div>
                );
              })}
            </>
          )}
        </>
      ) : (
        <p className="text-sm italic text-ink-faint">No extraction (routed away).</p>
      )}

      <div className="mt-6 flex gap-2">
        <ActionButton onClick={() => onReview("approved")} label="Approve" />
        <ActionButton onClick={() => onReview("edited")} label="Edit fields" />
        <ActionButton onClick={() => onReview("rejected")} label="Reject" />
      </div>
      {item.status !== "pending" && (
        <p className="mt-3 text-xs text-sage">
          {item.status === "approved" && "Approved — sent to ERP"}
          {item.status === "rejected" && "Rejected — returned to sender"}
          {item.status === "edited" && "Edited — changes recorded"}
        </p>
      )}
    </section>
  );
}

function FieldRow({
  label,
  value,
  flag,
}: {
  label: string;
  value: string | null;
  flag?: FieldFlag;
}) {
  return (
    <tr>
      <td className="w-40 py-1.5 align-top text-sm text-ink-soft">{label}</td>
      <td className="py-1.5 text-sm">
        {value === null || value === undefined ? (
          <span className="italic text-ink-faint">not found</span>
        ) : (
          <span className="text-ink">{value}</span>
        )}
        {flag?.in_band && <ConfBadge value={flag.raw_confidence} />}
      </td>
    </tr>
  );
}

function ConfBadge({ value }: { value: number }) {
  return (
    <span className="ml-2 rounded bg-ship-bg px-1.5 py-0.5 font-mono text-[11px] text-ship">
      {value.toFixed(2)}
    </span>
  );
}

function ActionButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className="flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink transition hover:border-ink-faint active:scale-[0.98]"
    >
      {label}
    </button>
  );
}
