import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { listUsersInOrg } from "@/lib/users";
import { MembersPanel } from "./members-panel";

export default async function MembersPage() {
  const session = await auth();
  const user = session?.user as
    | { email?: string | null; orgId?: string; role?: string }
    | undefined;

  // authorisation on the server -- hiding the nav link is not authorisation
  if (!user?.orgId || !user.email || user.role !== "admin") redirect("/");

  const members = listUsersInOrg(user.orgId);

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-10">
      <header className="mb-8 flex items-baseline justify-between border-b border-line pb-5">
        <div>
          <h1 className="text-xl font-medium text-ink">Members</h1>
          <p className="mt-0.5 text-sm text-ink-soft">
            People with access to <span className="font-mono">{user.orgId}</span>
          </p>
        </div>
        <Link
          href="/"
          className="text-xs text-ink-faint underline underline-offset-2 hover:text-ink-soft"
        >
          Back to queue
        </Link>
      </header>

      <MembersPanel orgId={user.orgId} currentEmail={user.email} members={members} />
    </main>
  );
}
