import type { Metadata } from "next";
import { Marketplace } from "@/components/marketplace/marketplace";

export const metadata: Metadata = {
  title: "Marketplace de Leads para Agentes",
  description:
    "Marketplace de FSG Seguros para agentes. Selecciona leads de seguro de vida por municipio, antigüedad y cantidad. Ambiente de demostración.",
};
export default function LeadsPage() {
  return <Marketplace />;
}
