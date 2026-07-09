import NextAuth from "next-auth";
import { authConfig } from "./auth.config";

// Edge-safe: authConfig has no providers and no database imports.
export const { auth: middleware } = NextAuth(authConfig);

export const config = {
  matcher: ["/((?!api/auth|login|_next/static|_next/image|favicon.ico).*)"],
};
