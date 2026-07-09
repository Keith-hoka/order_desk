import Link from "next/link";
import { redirect } from "next/navigation";
import { auth, signIn } from "@/auth";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const session = await auth();
  if (session?.user) redirect("/");
  const { error } = await searchParams;

  async function login(formData: FormData) {
    "use server";
    try {
      await signIn("credentials", {
        email: formData.get("email"),
        password: formData.get("password"),
        redirectTo: "/",
      });
    } catch (e) {
      // next-auth throws a redirect on success; rethrow it
      if ((e as { digest?: string })?.digest?.startsWith("NEXT_REDIRECT")) throw e;
      redirect("/login?error=1");
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="text-xl font-medium text-ink">order_desk</h1>
        <p className="mt-0.5 mb-8 text-sm text-ink-soft">Sign in to the review queue</p>

        <form action={login} className="flex flex-col gap-3">
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
            placeholder="Password"
            className="rounded border border-line px-3 py-2 text-sm text-ink outline-none focus:border-ship"
          />
          {error && (
            <p className="text-sm text-brick">Invalid email or password.</p>
          )}
          <button
            type="submit"
            className="mt-1 rounded bg-ship px-3 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Sign in
          </button>
        </form>

        <p className="mt-4 text-sm text-ink-soft">
          No account?{" "}
          <Link href="/signup" className="underline underline-offset-2 hover:text-ink">
            Create an organisation
          </Link>
        </p>

        <div className="mt-8 rounded border border-line bg-paper-soft p-4">
          <p className="mb-2 text-xs font-medium text-ink-soft">Demo accounts</p>
          <p className="font-mono text-xs text-ink-faint">
            demo-admin@order-desk.test · demo1234
          </p>
          <p className="font-mono text-xs text-ink-faint">
            demo-reviewer@order-desk.test · demo1234
          </p>
          <p className="mt-2 text-xs text-ink-faint">
            Both belong to the demo org, which owns the sample review queue.
          </p>
        </div>
      </div>
    </main>
  );
}
