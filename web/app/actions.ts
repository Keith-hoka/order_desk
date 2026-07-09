"use server";

import { revalidatePath } from "next/cache";
import { submitReview } from "@/lib/api-server";
import type { ReviewStatus } from "@/lib/types";

/**
 * Submit a review decision. Runs on the server: the session's org scope is
 * minted into the API token, so a user can only act on their own org's items
 * (the backend returns 404 for anything else).
 */
export async function submitReviewAction(
  id: string,
  action: ReviewStatus,
  edits: Record<string, string> = {}
): Promise<void> {
  await submitReview(id, action, edits);
  revalidatePath("/");
}
