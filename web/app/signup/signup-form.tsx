"use client";

import { useActionState } from "react";
import { signupAction, type SignupResult } from "./actions";

const EMPTY: SignupResult = {};

export function SignupForm() {
  const [state, action, pending] = useActionState(signupAction, EMPTY);

  return (
    <form action={action} className="flex flex-col gap-3">
      <input
        name="email"
        type="email"
        required
        placeholder="you@company.com"
        className="rounded border border-line px-3 py-2 text-sm text-ink outline-none focus:border-ship"
      />
      <input
        name="password"
        type="password"
        required
        minLength={8}
        placeholder="Password (8+ characters)"
        className="rounded border border-line px-3 py-2 text-sm text-ink outline-none focus:border-ship"
      />
      {state.error && <p className="text-sm text-brick">{state.error}</p>}
      <button
        type="submit"
        disabled={pending}
        className="mt-1 rounded bg-ship px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
      >
        {pending ? "Creating account…" : "Create account"}
      </button>
    </form>
  );
}
