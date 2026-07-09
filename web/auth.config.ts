/**
 * Edge-safe Auth.js config (Phase 11, block B).
 *
 * Middleware runs on the Edge runtime, which cannot load native Node modules
 * (better-sqlite3 pulls in `fs`). So the pieces middleware needs -- session
 * shape, callbacks, the sign-in page -- live here, free of database imports.
 * The credentials provider, which must hit the user store, is added in auth.ts,
 * which only runs in the Node runtime.
 */
import type { NextAuthConfig } from "next-auth";

export const authConfig = {
  session: { strategy: "jwt" },
  providers: [], // added in auth.ts (Node runtime only)
  pages: { signIn: "/login" },
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.orgId = (user as { orgId: string }).orgId;
        token.role = (user as { role: string }).role;
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        (session.user as { orgId?: string }).orgId = token.orgId as string;
        (session.user as { role?: string }).role = token.role as string;
      }
      return session;
    },
    authorized({ auth }) {
      return !!auth?.user; // middleware: signed-in users only
    },
  },
} satisfies NextAuthConfig;
