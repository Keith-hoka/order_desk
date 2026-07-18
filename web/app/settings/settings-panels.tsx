"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { saveMailboxAction, saveSlackWebhookAction } from "../actions";
import type { MailboxSetting, WebhookSetting } from "@/lib/types";

/** The org's mailbox: the queue's Extract button pulls recent unseen emails
 *  from it. Stored server-side so a customer never needs .env access. */
function MailboxPanel({ mailbox, isAdmin }: { mailbox: MailboxSetting; isAdmin: boolean }) {
  const [host, setHost] = useState("");
  const [address, setAddress] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function save(h: string, a: string, p: string) {
    setError(null);
    startTransition(async () => {
      const result = await saveMailboxAction(h, a, p);
      if ("error" in result) {
        setError(result.error);
        return;
      }
      setHost("");
      setAddress("");
      setPassword("");
      router.refresh();
    });
  }

  return (
    <section className="rounded-lg border border-line bg-surface p-4">
      <p className="mb-2 text-[11px] uppercase tracking-wide text-ink-faint">
        Mailbox — where Extract pulls emails from
      </p>
      <p className="mb-3 text-xs text-ink-soft">
        {mailbox.configured ? (
          <>
            pulling from <span className="font-mono">{mailbox.address}</span> via{" "}
            <span className="font-mono">{mailbox.host}</span>
          </>
        ) : (
          "not configured — the Extract button on the queue is disabled"
        )}
      </p>
      {isAdmin ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Mailbox address"
              autoComplete="username"
              className="min-w-0 flex-1 rounded border border-line px-2 py-1.5 text-sm text-ink outline-none focus:border-ship"
            />
            <input
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder="IMAP host, e.g. imap.gmail.com"
              className="min-w-0 flex-1 rounded border border-line px-2 py-1.5 text-sm text-ink outline-none focus:border-ship"
            />
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="App password — NOT your email password"
              type="password"
              autoComplete="current-password"
              className="min-w-0 flex-1 rounded border border-line px-2 py-1.5 text-sm text-ink outline-none focus:border-ship"
            />
            <button
              onClick={() => save(host, address, password)}
              disabled={pending || !host.trim() || !address.trim() || !password.trim()}
              className="rounded-lg border border-line bg-surface px-4 py-2 text-sm text-ink transition enabled:hover:border-ink-faint disabled:cursor-not-allowed disabled:opacity-40"
            >
              {pending ? "Saving…" : "Save"}
            </button>
            {mailbox.configured && (
              <button
                onClick={() => save("", "", "")}
                disabled={pending}
                className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink-soft transition enabled:hover:border-ink-faint disabled:opacity-40"
              >
                Clear
              </button>
            )}
          </div>
          <p className="mt-2 rounded bg-amber-bg px-2 py-1.5 text-[11px] leading-relaxed text-amber">
            Do <strong>not</strong> enter your email login password here. Use a dedicated{" "}
            <strong>app password</strong> issued by your mail provider — for Gmail, turn on
            2-Step Verification, then create one at myaccount.google.com/apppasswords.
          </p>
        </>
      ) : (
        <p className="text-[11px] text-ink-faint">an org admin can change this</p>
      )}
      {error && <p className="mt-2 text-xs text-brick">{error}</p>}
    </section>
  );
}

/** The org's Slack webhook: approvals notify this channel. */
function SlackPanel({ webhook, isAdmin }: { webhook: WebhookSetting; isAdmin: boolean }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  function save(next: string) {
    setError(null);
    startTransition(async () => {
      const result = await saveSlackWebhookAction(next);
      if ("error" in result) {
        setError(result.error);
        return;
      }
      setUrl("");
      router.refresh();
    });
  }

  return (
    <section className="rounded-lg border border-line bg-surface p-4">
      <p className="mb-2 text-[11px] uppercase tracking-wide text-ink-faint">
        Slack notifications — your org&apos;s incoming-webhook URL
      </p>
      <p className="mb-3 text-xs text-ink-soft">
        {webhook.configured ? (
          <>
            notifying <span className="font-mono">{webhook.masked}</span>
          </>
        ) : (
          "not configured — approvals fall back to the server-wide webhook, if one is set"
        )}
      </p>
      {isAdmin ? (
        <div className="flex items-center gap-2">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://hooks.slack.com/services/…"
            className="min-w-0 flex-1 rounded border border-line px-2 py-1.5 text-sm text-ink outline-none focus:border-ship"
          />
          <button
            onClick={() => save(url)}
            disabled={pending || url.trim() === ""}
            className="rounded-lg border border-line bg-surface px-4 py-2 text-sm text-ink transition enabled:hover:border-ink-faint disabled:cursor-not-allowed disabled:opacity-40"
          >
            {pending ? "Saving…" : "Save"}
          </button>
          {webhook.configured && (
            <button
              onClick={() => save("")}
              disabled={pending}
              className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink-soft transition enabled:hover:border-ink-faint disabled:opacity-40"
            >
              Clear
            </button>
          )}
        </div>
      ) : (
        <p className="text-[11px] text-ink-faint">an org admin can change this</p>
      )}
      {error && <p className="mt-2 text-xs text-brick">{error}</p>}
    </section>
  );
}

export function SettingsPanels({
  mailbox,
  webhook,
  isAdmin,
}: {
  mailbox: MailboxSetting;
  webhook: WebhookSetting;
  isAdmin: boolean;
}) {
  return (
    <div className="flex flex-col gap-6">
      <MailboxPanel mailbox={mailbox} isAdmin={isAdmin} />
      <SlackPanel webhook={webhook} isAdmin={isAdmin} />
    </div>
  );
}
