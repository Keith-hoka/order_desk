/**
 * UI-side user store (Phase 11, block B).
 *
 * Holds the human users who sign in to the review UI: email, password hash,
 * the org they belong to, and their role. Backed by SQLite so accounts survive
 * restarts. This is deliberately separate from the API's tenancy model (which
 * owns orgs, plans and quotas): the UI authenticates people, the API authorises
 * machine calls. A production deployment would unify them behind one identity
 * service. Honest edge, stated plainly.
 */
import Database from "better-sqlite3";
import bcrypt from "bcryptjs";
import path from "node:path";

export type Role = "admin" | "reviewer";

export interface User {
  email: string;
  orgId: string;
  role: Role;
}

const DB_PATH = process.env.USERS_DB_PATH ?? path.join(process.cwd(), "users.db");

let _db: Database.Database | null = null;

function db(): Database.Database {
  if (_db) return _db;
  _db = new Database(DB_PATH);
  _db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      email TEXT PRIMARY KEY,
      password_hash TEXT NOT NULL,
      org_id TEXT NOT NULL,
      role TEXT NOT NULL
    )
  `);
  return _db;
}

export function getUser(email: string): User | null {
  const row = db()
    .prepare("SELECT email, org_id, role FROM users WHERE email = ?")
    .get(email.toLowerCase()) as { email: string; org_id: string; role: Role } | undefined;
  if (!row) return null;
  return { email: row.email, orgId: row.org_id, role: row.role };
}

export function createUser(
  email: string,
  password: string,
  orgId: string,
  role: Role
): User {
  const hash = bcrypt.hashSync(password, 10);
  db()
    .prepare(
      `INSERT INTO users (email, password_hash, org_id, role) VALUES (?, ?, ?, ?)
       ON CONFLICT (email) DO UPDATE SET
         password_hash = excluded.password_hash,
         org_id = excluded.org_id,
         role = excluded.role`
    )
    .run(email.toLowerCase(), hash, orgId, role);
  return { email: email.toLowerCase(), orgId, role };
}

export function verifyUser(email: string, password: string): User | null {
  const row = db()
    .prepare("SELECT email, password_hash, org_id, role FROM users WHERE email = ?")
    .get(email.toLowerCase()) as
    | { email: string; password_hash: string; org_id: string; role: Role }
    | undefined;
  if (!row) return null;
  if (!bcrypt.compareSync(password, row.password_hash)) return null;
  return { email: row.email, orgId: row.org_id, role: row.role };
}

/** Delete a user, scoped to an org so a caller can never remove another tenant's. */
export function removeUser(email: string, orgId: string): boolean {
  const info = db()
    .prepare("DELETE FROM users WHERE email = ? AND org_id = ?")
    .run(email.toLowerCase(), orgId);
  return info.changes > 0;
}

export function listUsersInOrg(orgId: string): User[] {
  const rows = db()
    .prepare("SELECT email, org_id, role FROM users WHERE org_id = ? ORDER BY email")
    .all(orgId) as { email: string; org_id: string; role: Role }[];
  return rows.map((r) => ({ email: r.email, orgId: r.org_id, role: r.role }));
}

/** A newly registered user gets their own org (and is its admin). */
export function newOrgId(): string {
  return `org-${crypto.randomUUID().slice(0, 8)}`;
}

/** The org that owns the pre-tenancy Phase 7 review queue. */
export const DEMO_ORG_ID = "org-demo";

/** Seed demo accounts so the queue is explorable without registering. */
export function seedDemoUsers(): void {
  if (!getUser("demo-admin@order-desk.test")) {
    createUser("demo-admin@order-desk.test", "demo1234", DEMO_ORG_ID, "admin");
  }
  if (!getUser("demo-reviewer@order-desk.test")) {
    createUser("demo-reviewer@order-desk.test", "demo1234", DEMO_ORG_ID, "reviewer");
  }
}
