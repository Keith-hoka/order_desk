"use server";

import { revalidatePath } from "next/cache";
import { auth } from "@/auth";
import { createUser, getUser, removeUser } from "@/lib/users";

export interface MemberActionResult {
  error?: string;
  ok?: string;
}

async function requireAdmin(): Promise<{ orgId: string; email: string } | null> {
  const session = await auth();
  const actor = session?.user as
    | { email?: string | null; orgId?: string; role?: string }
    | undefined;
  if (!actor?.orgId || !actor.email || actor.role !== "admin") return null;
  return { orgId: actor.orgId, email: actor.email };
}

/**
 * Add a reviewer to the signed-in admin's org.
 *
 * The org comes from the *session*, never the form: a client can tamper with
 * form fields, so trusting an org_id from the request would let an admin plant
 * users in another tenant. The role is fixed to reviewer -- granting admin is a
 * privilege escalation that deserves a real flow (an owner role, or an existing
 * admin explicitly promoting someone), not a dropdown on an invite form.
 *
 * Honest scope: a simplified invite. Production would email a single-use
 * invitation and let the invitee set their own password.
 */
export async function createUserAction(
  _prev: MemberActionResult,
  formData: FormData
): Promise<MemberActionResult> {
  const actor = await requireAdmin();
  if (!actor) return { error: "Only an admin can add members." };

  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");

  if (!email || !password) return { error: "Email and password are required." };
  if (password.length < 8) return { error: "Password must be at least 8 characters." };
  if (getUser(email)) return { error: `${email} already has an account.` };

  createUser(email, password, actor.orgId, "reviewer"); // org from session, role fixed
  revalidatePath("/members");
  return { ok: `Added ${email} as a reviewer.` };
}

/**
 * Remove a member from the admin's own org.
 *
 * Guards, in order: the target must exist, must belong to the caller's org
 * (never another tenant's), and must not be the caller. Admins are not
 * removable through this form -- an org must keep at least one admin, and the
 * simplest way to guarantee that is to only ever remove reviewers.
 */
export async function removeUserAction(
  _prev: MemberActionResult,
  formData: FormData
): Promise<MemberActionResult> {
  const actor = await requireAdmin();
  if (!actor) return { error: "Only an admin can remove members." };

  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const target = getUser(email);

  if (!target) return { error: "No such member." };
  if (target.orgId !== actor.orgId) return { error: "No such member." }; // no cross-tenant leak
  if (target.email === actor.email) return { error: "You cannot remove yourself." };
  if (target.role === "admin") return { error: "Admins cannot be removed here." };

  removeUser(email, actor.orgId); // org-scoped delete
  revalidatePath("/members");
  return { ok: `Removed ${email}.` };
}
