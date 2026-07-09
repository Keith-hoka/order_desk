"use client";

import { useActionState } from "react";
import { createUserAction, removeUserAction, type MemberActionResult } from "./actions";
import type { User } from "@/lib/users";

const EMPTY: MemberActionResult = {};

function Feedback({ state }: { state: MemberActionResult }) {
  if (state.error) return <p className="text-sm text-brick">{state.error}</p>;
  if (state.ok) return <p className="text-sm text-sage">{state.ok}</p>;
  return null;
}

export function MembersPanel({
  orgId,
  currentEmail,
  members,
}: {
  orgId: string;
  currentEmail: string;
  members: User[];
}) {
  const [addState, addAction, adding] = useActionState(createUserAction, EMPTY);
  const [removeState, removeAction, removing] = useActionState(removeUserAction, EMPTY);

  return (
    <>
      <ul className="mb-3 flex flex-col gap-px overflow-hidden rounded border border-line">
        {members.map((m) => (
          <li
            key={m.email}
            className="flex items-baseline justify-between gap-4 bg-paper px-4 py-3"
          >
            <span className="font-mono text-sm text-ink">{m.email}</span>
            <div className="flex items-baseline gap-4">
              <span className="text-xs text-ink-faint">{m.role}</span>
              {m.role === "reviewer" && m.email !== currentEmail ? (
                <form action={removeAction}>
                  <input type="hidden" name="email" value={m.email} />
                  <button
                    type="submit"
                    disabled={removing}
                    className="text-xs text-brick underline underline-offset-2 hover:opacity-80 disabled:opacity-40"
                  >
                    Remove
                  </button>
                </form>
              ) : (
                <span className="text-xs text-ink-faint opacity-40">—</span>
              )}
            </div>
          </li>
        ))}
      </ul>
      <div className="mb-10 min-h-5">
        <Feedback state={removeState} />
      </div>

      <section className="rounded border border-line p-5">
        <h2 className="mb-1 text-sm font-medium text-ink">Add a reviewer</h2>
        <p className="mb-4 text-xs text-ink-faint">
          They join <span className="font-mono">{orgId}</span> and see only this
          organisation&apos;s queue.
        </p>
        <form action={addAction} className="flex flex-col gap-3">
          <input
            name="email"
            type="email"
            required
            placeholder="teammate@company.com"
            className="rounded border border-line px-3 py-2 text-sm text-ink outline-none focus:border-ship"
          />
          <input
            name="password"
            type="password"
            required
            minLength={8}
            placeholder="Temporary password (8+ characters)"
            className="rounded border border-line px-3 py-2 text-sm text-ink outline-none focus:border-ship"
          />
          <button
            type="submit"
            disabled={adding}
            className="mt-1 self-start rounded bg-ship px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {adding ? "Adding…" : "Add reviewer"}
          </button>
        </form>
        <div className="mt-3 min-h-5">
          <Feedback state={addState} />
        </div>
        <p className="mt-3 text-xs text-ink-faint">
          Simplified invite: an admin sets the password directly, and new members are
          reviewers. Promoting someone to admin, and emailing a single-use invitation
          link, are production flows this skeleton leaves out.
        </p>
      </section>
    </>
  );
}
