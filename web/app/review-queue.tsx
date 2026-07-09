"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { submitReviewAction } from "./actions";
import type { FieldFlag, Fulfillment, ReviewItem, ReviewStatus } from "@/lib/types";

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

export function ReviewQueue({ items }: { items: ReviewItem[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(
    items.length > 0 ? items[0].id : null
  );
  const [pending, startTransition] = useTransition();
  const [outcome, setOutcome] = useState<{ id: string; fulfillment?: Fulfillment | null } | null>(
    null
  );
  const router = useRouter();

  const selected = items.find((it) => it.id === selectedId) ?? null;

  function handleReview(action: ReviewStatus, edits: Record<string, string> = {}) {
    if (!selected) return;
    startTransition(async () => {
      const reviewed = await submitReviewAction(selected.id, action, edits);
      setOutcome({ id: reviewed.id, fulfillment: reviewed.fulfillment });
      router.refresh();
    });
  }

  if (items.length === 0) {
    return (
      <div className="grid place-items-center py-20 text-ink-faint">
        <p>No exceptions in your organisation&apos;s queue.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-[260px_minmax(0,1fr)] gap-8">
      <QueueList items={items} selectedId={selectedId} onSelect={setSelectedId} />
      {selected ? (
        <div className={pending ? "opacity-60 transition-opacity" : ""}>
          <Detail
            item={selected}
            onReview={handleReview}
            outcome={outcome?.id === selected.id ? outcome.fulfillment : undefined}
          />
        </div>
      ) : (
        <div className="grid place-items-center text-ink-faint">
          <p>Select an exception.</p>
        </div>
      )}
    </div>
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
  outcome,
}: {
  item: ReviewItem;
  onReview: (action: ReviewStatus, edits?: Record<string, string>) => void;
  outcome?: Fulfillment | null;
}) {
  const reason = reasonFor(item);
  const style = KIND_STYLE[reason.kind];
  const ex = item.extraction;
  const flagMap = new Map(item.field_flags.map((f) => [f.path, f]));

  const [editing, setEditing] = useState(false);
  // only paths the reviewer actually changed; an unchanged field must never
  // reach the flywheel as a "correction"
  const [draft, setDraft] = useState<Record<string, string>>({});

  function stage(path: string, original: string, next: string) {
    setDraft((prev) => {
      const copy = { ...prev };
      if (next === original) delete copy[path];
      else copy[path] = next;
      return copy;
    });
  }

  function save() {
    const edits = draft;
    setEditing(false);
    setDraft({});
    // nothing changed -- this is an approval, not a correction
    onReview(Object.keys(edits).length === 0 ? "approved" : "edited", edits);
  }

  function cancel() {
    setEditing(false);
    setDraft({});
  }

  return (
    <section className="pl-1">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-mono text-xs text-ink-faint">{item.id}</span>
        <span className="ml-auto text-xs text-ink-faint">
          priority {item.priority.toFixed(1)}
        </span>
      </div>
      <h2 className="mb-4 text-lg font-medium leading-snug text-ink">{item.subject}</h2>

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
              <FieldRow
                label="PO number"
                path="customer_po_text"
                value={ex.customer_po_text}
                flag={flagMap.get("customer_po_text")}
                editing={editing}
                onStage={stage}
              />
              <FieldRow
                label="Delivery address"
                path="delivery_address_text"
                value={ex.delivery_address_text}
                flag={flagMap.get("delivery_address_text")}
                editing={editing}
                onStage={stage}
              />
              <FieldRow
                label="Buyer"
                path="buyer_name_text"
                value={ex.buyer_name_text}
                flag={flagMap.get("buyer_name_text")}
                editing={editing}
                onStage={stage}
              />
              <FieldRow
                label="Requested date"
                path="requested_date_text"
                value={ex.requested_date_text}
                flag={flagMap.get("requested_date_text")}
                editing={editing}
                onStage={stage}
              />
            </tbody>
          </table>
          {ex.line_items.length > 0 && (
            <>
              <p className="mb-1 mt-4 text-[11px] text-ink-faint">Line items</p>
              {ex.line_items.map((li, i) => {
                const pf = flagMap.get(`line_items.${i}.product_text`);
                const qty =
                  li.quantity !== null ? `${li.quantity} ${li.unit_text ?? ""}`.trim() : null;
                return (
                  <div
                    key={i}
                    className="flex items-baseline justify-between gap-3 border-b border-line py-2"
                  >
                    {editing ? (
                      <>
                        <input
                          defaultValue={li.product_text}
                          onChange={(e) =>
                            stage(`line_items.${i}.product_text`, li.product_text, e.target.value)
                          }
                          className="min-w-0 flex-1 rounded border border-line px-2 py-1 text-sm text-ink outline-none focus:border-ship"
                        />
                        <input
                          defaultValue={li.quantity ?? ""}
                          inputMode="numeric"
                          onChange={(e) =>
                            stage(
                              `line_items.${i}.quantity`,
                              String(li.quantity ?? ""),
                              e.target.value
                            )
                          }
                          className="w-20 rounded border border-line px-2 py-1 text-right font-mono text-xs text-ink outline-none focus:border-ship"
                        />
                      </>
                    ) : (
                      <>
                        <span className="text-sm text-ink">
                          {li.product_text}
                          {pf?.in_band && <ConfBadge value={pf.raw_confidence} />}
                        </span>
                        <span className="font-mono text-xs text-ink-soft">
                          {qty ?? <span className="italic text-ink-faint">qty not found</span>}
                        </span>
                      </>
                    )}
                  </div>
                );
              })}
            </>
          )}
        </>
      ) : (
        <p className="text-sm italic text-ink-faint">No extraction (routed away).</p>
      )}

      <div className="mt-6 flex items-center gap-2">
        {editing ? (
          <>
            <ActionButton onClick={save} label="Save review" />
            <ActionButton onClick={cancel} label="Cancel" />
            <span className="ml-1 text-xs text-ink-faint">
              {Object.keys(draft).length === 0
                ? "no changes — saving approves as-is"
                : `${Object.keys(draft).length} field${Object.keys(draft).length === 1 ? "" : "s"} changed`}
            </span>
          </>
        ) : (
          <>
            <ActionButton onClick={() => onReview("approved")} label="Approve" />
            <ActionButton onClick={() => setEditing(true)} label="Edit fields" />
            <ActionButton onClick={() => onReview("rejected")} label="Reject" />
          </>
        )}
      </div>

      {outcome !== undefined && <Outcome fulfillment={outcome} />}
      {outcome === undefined && item.status !== "pending" && (
        <p className="mt-3 text-xs text-ink-faint">
          {item.status === "approved" && "Approved"}
          {item.status === "rejected" && "Rejected — returned to sender"}
          {item.status === "edited" &&
            `Edited — ${Object.keys(item.edits).length} field${Object.keys(item.edits).length === 1 ? "" : "s"} corrected`}
        </p>
      )}
    </section>
  );
}

/** Report what the backend actually did, rather than asserting an outcome. */
function Outcome({ fulfillment }: { fulfillment?: Fulfillment | null }) {
  if (!fulfillment) {
    return (
      <p className="mt-3 text-xs text-ink-faint">
        Recorded — no ERP sink configured, so nothing was sent downstream.
      </p>
    );
  }
  if (fulfillment.submitted) {
    return (
      <p className="mt-3 text-xs text-sage">
        Sent to ERP — <span className="font-mono">{fulfillment.order_id}</span>
      </p>
    );
  }
  return (
    <p className="mt-3 text-xs text-brick">
      Held — {fulfillment.reason}
      {fulfillment.unresolved.length > 0 && (
        <> (unresolved: {fulfillment.unresolved.join(", ")})</>
      )}
    </p>
  );
}

function FieldRow({
  label,
  path,
  value,
  flag,
  editing,
  onStage,
}: {
  label: string;
  path: string;
  value: string | null;
  flag?: FieldFlag;
  editing: boolean;
  onStage: (path: string, original: string, next: string) => void;
}) {
  return (
    <tr className="border-b border-line">
      <td className="w-40 py-2 align-top text-xs text-ink-faint">{label}</td>
      <td className="py-2 text-sm text-ink">
        {editing ? (
          <input
            defaultValue={value ?? ""}
            onChange={(e) => onStage(path, value ?? "", e.target.value)}
            className="w-full rounded border border-line px-2 py-1 text-sm text-ink outline-none focus:border-ship"
          />
        ) : (
          <>
            {value ?? <span className="italic text-ink-faint">not found</span>}
            {flag?.in_band && <ConfBadge value={flag.raw_confidence} />}
          </>
        )}
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
