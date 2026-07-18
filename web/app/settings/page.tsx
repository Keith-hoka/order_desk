import Link from "next/link";
import { auth } from "@/auth";
import { getMailbox, getSlackWebhook } from "@/lib/api-server";
import { SettingsPanels } from "./settings-panels";
import type { MailboxSetting, WebhookSetting } from "@/lib/types";

export default async function SettingsPage() {
  const session = await auth();
  const user = session?.user as { role?: string } | undefined;

  let mailbox: MailboxSetting = { configured: false, host: null, address: null };
  let webhook: WebhookSetting = { configured: false, masked: null };
  let error: string | null = null;
  try {
    [mailbox, webhook] = await Promise.all([getMailbox(), getSlackWebhook()]);
  } catch (e) {
    error = e instanceof Error ? e.message : "unknown error";
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-10">
      <header className="mb-8 flex items-baseline justify-between border-b border-line pb-5">
        <div>
          <h1 className="text-xl font-medium text-ink">Settings</h1>
          <p className="mt-0.5 text-sm text-ink-soft">
            Your organisation&apos;s mailbox and notification channel
          </p>
        </div>
        <Link
          href="/"
          className="text-xs text-ink-faint underline underline-offset-2 hover:text-ink-soft"
        >
          Back to queue
        </Link>
      </header>
      {error ? (
        <p className="font-mono text-sm text-ink-soft">{error}</p>
      ) : (
        <SettingsPanels mailbox={mailbox} webhook={webhook} isAdmin={user?.role === "admin"} />
      )}
    </main>
  );
}
