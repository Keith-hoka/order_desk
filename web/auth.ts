/**
 * Auth.js (NextAuth v5) configuration: credentials sign-in for the review UI.
 *
 * The session carries org_id and role, which drive both the UI (role-gated
 * views) and the server-side API bridge (a JWT minted per request with the
 * session's org scope). Credentials only -- no OAuth providers in this
 * skeleton.
 */
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { seedDemoUsers, verifyUser } from "@/lib/users";

seedDemoUsers();

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt" },
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      authorize: async (credentials) => {
        const email = credentials?.email as string | undefined;
        const password = credentials?.password as string | undefined;
        if (!email || !password) return null;
        const user = verifyUser(email, password);
        if (!user) return null;
        return { id: user.email, email: user.email, orgId: user.orgId, role: user.role };
      },
    }),
  ],
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
  },
  pages: { signIn: "/login" },
});
