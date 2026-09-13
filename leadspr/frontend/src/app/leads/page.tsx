import type { Metadata } from "next";
import { Marketplace } from "@/components/marketplace/marketplace";

export const metadata: Metadata = {
  title: "Marketplace de Leads para Agentes",
};
export default function LeadsPage() {
  return <Marketplace />;
}
