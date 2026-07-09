"use server";

import { signIn } from "@/auth";
import { createUser, getUser, newOrgId } from "@/lib/users";

export interface SignupResult {
  error?: string;
}

/**
 * Register a new account.
 *
 * A registering user founds their own organisation and becomes its admin, so
 * they start with an empty review queue -- they see their own org's exceptions,
 * never anyone else's. (The sample queue belongs to the demo org; sign in with a
 * demo account to explore it.)
 *
 * Honest scope: no email verification, no password reset, no org naming. Those
 * are production flows this skeleton leaves out.
 */
export async function signupAction(
  _prev: SignupResult,
  formData: FormData
): Promise<SignupResult> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");

  if (!email || !password) return { error: "Email and password are required." };
  if (password.length < 8) return { error: "Password must be at least 8 characters." };
  if (getUser(email)) return { error: "That email already has an account." };

  createUser(email, password, newOrgId(), "admin"); // own org, own admin

  await signIn("credentials", { email, password, redirectTo: "/" });
  return {};
}
