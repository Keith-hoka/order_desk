import Link from "next/link";
import { auth, signOut } from "@/auth";
import { fetchExceptions, getMailbox } from "@/lib/api-server";
import { ReviewQueue } from "./review-queue";
import type { MailboxSetting, ReviewItem } from "@/lib/types";

async function SignOutButton() {
  async function doSignOut() {
    "use server";
    await signOut({ redirectTo: "/login" });
  }
  return (
    <form action={doSignOut}>
      <button
        type="submit"
        className="text-xs text-ink-faint underline underline-offset-2 hover:text-ink-soft"
      >
        Sign out
      </button>
    </form>
  );
}

export default async function Page() {
  const session = await auth();
  const user = session?.user as
    | { email?: string | null; orgId?: string; role?: string }
    | undefined;

  let items: ReviewItem[] = [];
  let mailbox: MailboxSetting = { configured: false, host: null, address: null };
  let error: string | null = null;
  try {
    [items, mailbox] = await Promise.all([fetchExceptions(), getMailbox()]);
  } catch (e) {
    error = e instanceof Error ? e.message : "unknown error";
  }

  const flaggedCount = items.filter((it) => it.priority > 0).length;

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <header className="mb-8 flex items-baseline justify-between border-b border-line pb-5">
        <div>
          <h1 className="text-xl font-medium text-ink">Exception review</h1>
          <p className="mt-0.5 text-sm text-ink-soft">
            Extracted orders that need a human before they reach the ERP
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <p className="font-mono text-sm text-ink-faint">
            {flaggedCount} flagged · {items.length - flaggedCount} clean
          </p>
          <p className="text-xs text-ink-faint">
            {user?.email}
            {user?.orgId && (
              <>
                {" · "}
                <span className="font-mono">{user.orgId}</span>
                {" · "}
                {user.role}
              </>
            )}
          </p>
          <div className="flex items-baseline gap-3">
            <Link
              href="/settings"
              className="text-xs text-ink-faint underline underline-offset-2 hover:text-ink-soft"
            >
              Settings
            </Link>
            {user?.role === "admin" && (
              <Link
                href="/members"
                className="text-xs text-ink-faint underline underline-offset-2 hover:text-ink-soft"
              >
                Members
              </Link>
            )}
            <SignOutButton />
          </div>
        </div>
      </header>

      {error ? (
        <div className="grid place-items-center py-20 px-6">
          <div className="max-w-md text-center">
            <p className="mb-2 text-ink">Couldn&apos;t reach the review service.</p>
            <p className="font-mono text-sm text-ink-soft">{error}</p>
            <p className="mt-4 text-sm text-ink-faint">
              Start the API and set API_BASE and JWT_SECRET in .env.local.
            </p>
          </div>
        </div>
      ) : (
        <ReviewQueue items={items} mailbox={mailbox} />
      )}
    </main>
  );
}
