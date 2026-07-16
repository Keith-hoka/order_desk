"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { extractInboxAction, submitReviewAction } from "./actions";
import type {
  Extraction,
  FieldFlag,
  Fulfillment,
  LineItem,
  ReviewItem,
  ReviewStatus,
} from "@/lib/types";

// mirrors LINE_DELETED in order_desk.flywheel.corrections: a whole-line edit
// with this value removes the line item the model invented
const LINE_DELETED = "__deleted__";

// what a routed-away item edits against: an empty order with one blank line,
// so a reviewer can rescue an order the router missed (mirrors the backend's
// empty_extraction; the backend grows lines from the edit paths)
const EMPTY_EXTRACTION: Extraction = {
  customer_po_text: null,
  requested_date_text: null,
  delivery_address_text: null,
  buyer_name_text: null,
  notes: null,
  line_items: [
    { product_text: "", quantity: null, unit_text: null, unit_price_text: null, item_notes: null },
  ],
};

const BLANK_LINE: LineItem = {
  product_text: "",
  quantity: null,
  unit_text: null,
  unit_price_text: null,
  item_notes: null,
};

/** Rows to render: the extraction's lines plus any lines the edits created
 *  past the end (the backend appends those on apply). */
function lineRowCount(ex: Extraction, edits: Record<string, string>): number {
  let n = ex.line_items.length;
  for (const path of Object.keys(edits)) {
    const m = path.match(/^line_items\.(\d+)/);
    if (m) n = Math.max(n, parseInt(m[1], 10) + 1);
  }
  return n;
}

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
  const [outcome, setOutcome] = useState<{
    id: string;
    action: ReviewStatus;
    fulfillment?: Fulfillment | null;
  } | null>(null);
  const router = useRouter();

  const selected = items.find((it) => it.id === selectedId) ?? null;

  function handleReview(action: ReviewStatus, edits: Record<string, string> = {}) {
    if (!selected) return;
    startTransition(async () => {
      const reviewed = await submitReviewAction(selected.id, action, edits);
      setOutcome({ id: reviewed.id, action, fulfillment: reviewed.fulfillment });
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
      <div className="col-span-2">
        <ExtractPanel onExtracted={(id) => setSelectedId(id)} />
      </div>
      <QueueList items={items} selectedId={selectedId} onSelect={setSelectedId} />
      {selected ? (
        <div className={pending ? "opacity-60 transition-opacity" : ""}>
          <Detail
            item={selected}
            onReview={handleReview}
            outcome={outcome?.id === selected.id ? outcome : undefined}
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

/** Enter the mailbox address; the backend pulls its recent unseen emails
 *  through the live pipeline and lands them in the queue. Credentials live
 *  server-side (IMAP_HOST / IMAP_USERNAME / IMAP_PASSWORD). */
function ExtractPanel({ onExtracted }: { onExtracted: (id: string) => void }) {
  const [address, setAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function run() {
    setError(null);
    setNotice(null);
    startTransition(async () => {
      const result = await extractInboxAction(address);
      if ("error" in result) {
        setError(result.error);
        return;
      }
      setNotice(
        result.items.length === 0
          ? "No unseen emails in the mailbox."
          : `${result.items.length} email${result.items.length === 1 ? "" : "s"} extracted into the queue.`
      );
      if (result.items.length > 0) onExtracted(result.items[0].id);
      router.refresh();
    });
  }

  return (
    <div className="mb-6 rounded-lg border border-line bg-surface p-4">
      <p className="mb-2 text-[11px] uppercase tracking-wide text-ink-faint">
        Extract from mailbox — pulls recent unseen emails through the live pipeline
        (OpenAI routing + the adapter on Modal)
      </p>
      <div className="flex items-center gap-2">
        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Mailbox address, e.g. orders@company.com"
          className="min-w-0 flex-1 rounded border border-line px-2 py-1.5 text-sm text-ink outline-none focus:border-ship"
        />
        <button
          onClick={run}
          disabled={pending || address.trim() === ""}
          className="rounded-lg border border-line bg-surface px-4 py-2 text-sm text-ink transition enabled:hover:border-ink-faint disabled:cursor-not-allowed disabled:opacity-40"
        >
          {pending ? "Extracting…" : "Extract"}
        </button>
        {pending && (
          <span className="text-xs text-ink-faint">
            may take a while — one pipeline run per email, and the adapter cold-starts
          </span>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-brick">{error}</p>}
      {notice && <p className="mt-2 text-xs text-sage">{notice}</p>}
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

function sameEdits(a: Record<string, string>, b: Record<string, string>): boolean {
  const ka = Object.keys(a);
  return ka.length === Object.keys(b).length && ka.every((k) => a[k] === b[k]);
}

/** Required-field gaps in the extraction after the reviewer's corrections.
 *  An approve claims the order is complete; the backend enforces the same
 *  rule with a 422. */
function missingRequiredFields(item: ReviewItem): string[] {
  // a routed-away item validates against the empty skeleton: everything is
  // missing until the reviewer builds the order, so Approve stays locked
  const ex = item.extraction ?? EMPTY_EXTRACTION;
  const eff = (path: string, value: string | null) => item.edits[path] ?? value;
  const missing: string[] = [];
  if (!eff("customer_po_text", ex.customer_po_text)) missing.push("PO number");
  if (!eff("delivery_address_text", ex.delivery_address_text)) missing.push("Delivery address");
  if (!eff("buyer_name_text", ex.buyer_name_text)) missing.push("Buyer");
  if (!eff("requested_date_text", ex.requested_date_text)) missing.push("Requested date");
  const rows = lineRowCount(ex, item.edits);
  for (let i = 0; i < rows; i++) {
    if (item.edits[`line_items.${i}`] === LINE_DELETED) continue;
    const li = ex.line_items[i] ?? BLANK_LINE;
    if (!eff(`line_items.${i}.product_text`, li.product_text))
      missing.push(`line ${i + 1} product`);
    if (!eff(`line_items.${i}.quantity`, li.quantity !== null ? String(li.quantity) : null))
      missing.push(`line ${i + 1} quantity`);
  }
  return missing;
}

/** Approve sends (or amends) an order; it greys out once the current
 *  corrections are in the ERP, and re-arms when the fields change again. */
function approveDisabled(item: ReviewItem): boolean {
  if (item.status === "pending" || item.status === "rejected") return false;
  const f = item.fulfillment;
  // approved as-is with nothing ever sent (e.g. no sink configured): done.
  // edited with nothing sent yet: the corrections still await an approve.
  if (!f) return item.status === "approved";
  if (!f.submitted) return false; // held or errored -- approve retries
  // the store stamps for_edits on legacy records at load, so this compares
  // what was sent against what the reviewer has corrected since
  return sameEdits(f.for_edits ?? {}, item.edits);
}

function Detail({
  item,
  onReview,
  outcome,
}: {
  item: ReviewItem;
  onReview: (action: ReviewStatus, edits?: Record<string, string>) => void;
  outcome?: { action: ReviewStatus; fulfillment?: Fulfillment | null };
}) {
  const [editing, setEditing] = useState(false);
  // only paths the reviewer actually changed; an unchanged field must never
  // reach the flywheel as a "correction"
  const [draft, setDraft] = useState<Record<string, string>>({});
  // rows shown in edit mode; "Add line" extends it past the extraction's lines
  const [editLineCount, setEditLineCount] = useState(0);

  const reason = reasonFor(item);
  const style = KIND_STYLE[reason.kind];
  // a routed-away item shows its "no extraction" note until the reviewer acts;
  // in edit mode (or once corrections exist) it edits against the skeleton
  const ex =
    item.extraction ??
    (editing || Object.keys(item.edits).length > 0 ? EMPTY_EXTRACTION : null);
  const flagMap = new Map(item.field_flags.map((f) => [f.path, f]));
  const missing = missingRequiredFields(item);

  function stage(path: string, original: string, next: string) {
    setDraft((prev) => {
      const copy = { ...prev };
      if (next === original) delete copy[path];
      else copy[path] = next;
      return copy;
    });
  }

  function startEditing() {
    // seed with saved corrections: the backend replaces edits wholesale on each
    // submit, so starting from {} would silently drop prior corrections
    setDraft({ ...item.edits });
    setEditLineCount(lineRowCount(item.extraction ?? EMPTY_EXTRACTION, item.edits));
    setEditing(true);
  }

  function stageLineDelete(i: number, deleted: boolean) {
    setDraft((prev) => {
      const copy = { ...prev };
      if (deleted) copy[`line_items.${i}`] = LINE_DELETED;
      else delete copy[`line_items.${i}`];
      return copy;
    });
  }

  function save() {
    const edits = draft;
    setEditing(false);
    setDraft({});
    // two-step flow: saving records corrections only; Approve is the send.
    // nothing new over what is already saved -- just leave edit mode
    if (sameEdits(edits, item.edits)) return;
    onReview("edited", edits);
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
                edit={item.edits["customer_po_text"]}
                flag={flagMap.get("customer_po_text")}
                editing={editing}
                onStage={stage}
              />
              <FieldRow
                label="Delivery address"
                path="delivery_address_text"
                value={ex.delivery_address_text}
                edit={item.edits["delivery_address_text"]}
                flag={flagMap.get("delivery_address_text")}
                editing={editing}
                onStage={stage}
              />
              <FieldRow
                label="Buyer"
                path="buyer_name_text"
                value={ex.buyer_name_text}
                edit={item.edits["buyer_name_text"]}
                flag={flagMap.get("buyer_name_text")}
                editing={editing}
                onStage={stage}
              />
              <FieldRow
                label="Requested date"
                path="requested_date_text"
                value={ex.requested_date_text}
                edit={item.edits["requested_date_text"]}
                flag={flagMap.get("requested_date_text")}
                editing={editing}
                onStage={stage}
              />
            </tbody>
          </table>
          {(editing ? editLineCount : lineRowCount(ex, item.edits)) > 0 && (
            <>
              <p className="mb-1 mt-4 text-[11px] text-ink-faint">Line items</p>
              {Array.from(
                { length: editing ? editLineCount : lineRowCount(ex, item.edits) },
                (_, i) => {
                const li = ex.line_items[i] ?? BLANK_LINE;
                const pf = flagMap.get(`line_items.${i}.product_text`);
                const productEdit = item.edits[`line_items.${i}.product_text`];
                const qtyEdit = item.edits[`line_items.${i}.quantity`];
                const product = productEdit ?? li.product_text;
                const qtyShown = qtyEdit ?? (li.quantity !== null ? String(li.quantity) : null);
                const qty =
                  qtyShown !== null ? `${qtyShown} ${li.unit_text ?? ""}`.trim() : null;
                const deletedDraft = draft[`line_items.${i}`] === LINE_DELETED;
                const deletedSaved = item.edits[`line_items.${i}`] === LINE_DELETED;
                return (
                  <div
                    key={i}
                    className="flex items-baseline justify-between gap-3 border-b border-line py-2"
                  >
                    {editing ? (
                      deletedDraft ? (
                        <>
                          <span className="flex-1 text-sm text-ink-faint line-through">
                            {product}
                          </span>
                          <LineButton
                            label="Restore"
                            onClick={() => stageLineDelete(i, false)}
                          />
                        </>
                      ) : (
                        <>
                          <input
                            defaultValue={product}
                            onChange={(e) =>
                              stage(
                                `line_items.${i}.product_text`,
                                li.product_text,
                                e.target.value
                              )
                            }
                            className="min-w-0 flex-1 rounded border border-line px-2 py-1 text-sm text-ink outline-none focus:border-ship"
                          />
                          <input
                            defaultValue={qtyShown ?? ""}
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
                          <LineButton label="Remove" onClick={() => stageLineDelete(i, true)} />
                        </>
                      )
                    ) : deletedSaved ? (
                      <>
                        <span className="text-sm text-ink-faint line-through">
                          {li.product_text}
                        </span>
                        <RemovedBadge />
                      </>
                    ) : (
                      <>
                        <span className="text-sm text-ink">
                          {product}
                          {productEdit !== undefined && <EditedBadge />}
                          {pf?.in_band && <ConfBadge value={pf.raw_confidence} />}
                        </span>
                        <span className="font-mono text-xs text-ink-soft">
                          {qty ?? <span className="italic text-ink-faint">qty not found</span>}
                          {qtyEdit !== undefined && <EditedBadge />}
                        </span>
                      </>
                    )}
                  </div>
                );
                }
              )}
              {editing && (
                <div className="mt-2">
                  <LineButton
                    label="Add line"
                    onClick={() => setEditLineCount((c) => c + 1)}
                  />
                </div>
              )}
            </>
          )}
        </>
      ) : (
        <p className="text-sm italic text-ink-faint">
          No extraction (routed away). If the router got it wrong, Edit fields builds the
          order by hand.
        </p>
      )}

      <div className="mt-6 flex items-center gap-2">
        {editing ? (
          <>
            <ActionButton onClick={save} label="Save review" />
            <ActionButton onClick={cancel} label="Cancel" />
            <span className="ml-1 text-xs text-ink-faint">
              {sameEdits(draft, item.edits)
                ? "no changes to save"
                : `${Object.keys(draft).length} field${Object.keys(draft).length === 1 ? "" : "s"} changed`}
            </span>
          </>
        ) : (
          <>
            <ActionButton
              onClick={() => onReview("approved")}
              label="Approve"
              disabled={approveDisabled(item) || missing.length > 0}
            />
            <ActionButton onClick={startEditing} label="Edit fields" />
            <ActionButton onClick={() => onReview("rejected")} label="Reject" />
          </>
        )}
      </div>
      {!editing && missing.length > 0 && !approveDisabled(item) && (
        <p className="mt-2 text-xs text-brick">
          Approve needs every field filled — missing: {missing.join(", ")}
        </p>
      )}

      {/* a fresh submission reports exactly what the backend just did; otherwise
          fall back to the recorded fulfilment, which survives a refresh */}
      {outcome?.action === "edited" && (
        <p className="mt-3 text-xs text-ink-faint">
          Corrections saved — Approve sends the corrected order to the ERP.
        </p>
      )}
      {outcome?.action === "approved" && <Outcome fulfillment={outcome.fulfillment} />}
      {outcome === undefined && item.fulfillment != null && (
        <Outcome fulfillment={item.fulfillment} />
      )}
      {outcome === undefined && item.status !== "pending" && (
        <p className="mt-3 text-xs text-ink-faint">
          {item.status === "approved" &&
            (Object.keys(item.edits).length > 0
              ? `Approved — ${Object.keys(item.edits).length} field${Object.keys(item.edits).length === 1 ? "" : "s"} corrected`
              : "Approved")}
          {item.status === "rejected" && "Rejected — returned to sender"}
          {item.status === "edited" &&
            `Edited — ${Object.keys(item.edits).length} field${Object.keys(item.edits).length === 1 ? "" : "s"} corrected, awaiting approve`}
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
        {fulfillment.amends && (
          <>
            {" "}
            (amends <span className="font-mono">{fulfillment.amends}</span>)
          </>
        )}
      </p>
    );
  }
  const blockers = [
    ...(fulfillment.unresolved.length > 0
      ? [`unresolved: ${fulfillment.unresolved.join(", ")}`]
      : []),
    ...(fulfillment.issues ?? []),
  ];
  return (
    <p className="mt-3 text-xs text-brick">
      Held — {fulfillment.reason}
      {blockers.length > 0 && <> ({blockers.join("; ")})</>}
    </p>
  );
}

function FieldRow({
  label,
  path,
  value,
  edit,
  flag,
  editing,
  onStage,
}: {
  label: string;
  path: string;
  value: string | null;
  edit?: string;
  flag?: FieldFlag;
  editing: boolean;
  onStage: (path: string, original: string, next: string) => void;
}) {
  const shown = edit ?? value;
  return (
    <tr className="border-b border-line">
      <td className="w-40 py-2 align-top text-xs text-ink-faint">{label}</td>
      <td className="py-2 text-sm text-ink">
        {editing ? (
          <input
            defaultValue={shown ?? ""}
            onChange={(e) => onStage(path, value ?? "", e.target.value)}
            className="w-full rounded border border-line px-2 py-1 text-sm text-ink outline-none focus:border-ship"
          />
        ) : (
          <>
            {shown ?? <span className="italic text-ink-faint">not found</span>}
            {edit !== undefined && <EditedBadge />}
            {flag?.in_band && <ConfBadge value={flag.raw_confidence} />}
          </>
        )}
      </td>
    </tr>
  );
}

function EditedBadge() {
  return (
    <span className="ml-2 rounded bg-sage-bg px-1.5 py-0.5 font-mono text-[11px] text-sage">
      corrected
    </span>
  );
}

function RemovedBadge() {
  return (
    <span className="rounded bg-brick-bg px-1.5 py-0.5 font-mono text-[11px] text-brick">
      removed
    </span>
  );
}

function LineButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded border border-line px-2 py-1 text-xs text-ink-soft transition hover:border-ink-faint"
    >
      {label}
    </button>
  );
}

function ConfBadge({ value }: { value: number }) {
  return (
    <span className="ml-2 rounded bg-ship-bg px-1.5 py-0.5 font-mono text-[11px] text-ship">
      {value.toFixed(2)}
    </span>
  );
}

function ActionButton({
  onClick,
  label,
  disabled = false,
}: {
  onClick: () => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink transition enabled:hover:border-ink-faint enabled:active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
    >
      {label}
    </button>
  );
}
