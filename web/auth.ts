/**
 * Full Auth.js config: the edge-safe base plus the credentials provider.
 *
 * This module imports the SQLite user store, so it must only be used from the
 * Node runtime (route handlers, server components, server actions) -- never
 * from middleware. Middleware imports auth.config.ts instead.
 */
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { authConfig } from "./auth.config";
import { seedDemoUsers, verifyUser } from "@/lib/users";

seedDemoUsers();

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
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
});
