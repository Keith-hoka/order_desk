import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { SignupForm } from "./signup-form";

export default async function SignupPage() {
  const session = await auth();
  if (session?.user) redirect("/");

  return (
    <main className="grid min-h-screen place-items-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="text-xl font-medium text-ink">order_desk</h1>
        <p className="mt-0.5 mb-8 text-sm text-ink-soft">Create an organisation</p>

        <SignupForm />

        <p className="mt-4 text-xs text-ink-faint">
          You&apos;ll be the admin of a new organisation, starting with an empty queue.
          To explore the sample queue, sign in with a demo account instead.
        </p>

        <p className="mt-6 text-sm text-ink-soft">
          Already have an account?{" "}
          <Link href="/login" className="underline underline-offset-2 hover:text-ink">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
