import type { Metadata } from "next";
import { Dashboard } from "@/components/operations/dashboard";
import { hasAdminSession } from "@/lib/server/admin-session";

export const metadata: Metadata = {
  title: "Operaciones FSG",
  description:
    "Panel de FSG Seguros para administrar inventario de leads, precios, compras y sincronización con Google Sheets.",
};

export default async function AdminPage() {
  return <Dashboard initiallyAuthenticated={await hasAdminSession()} />;
}
