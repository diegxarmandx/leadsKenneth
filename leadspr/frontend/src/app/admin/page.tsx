import type { Metadata } from "next";
import { Dashboard } from "@/components/operations/dashboard";
import { hasAdminSession } from "@/lib/server/admin-session";

export const metadata: Metadata = { title: "Administración" };

export default async function AdminPage() {
  return <Dashboard initiallyAuthenticated={await hasAdminSession()} />;
}
