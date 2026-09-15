import type { Metadata } from "next";
import { PageIntro } from "@/components/page-intro";

export const metadata: Metadata = {
  title: "Pago cerrado",
  robots: { index: false, follow: false },
};

export default function CancelPage() {
  return (
    <PageIntro
      eyebrow="FSG Seguros"
      title="Saliste del proceso de pago."
      href="/leads"
      linkLabel="Volver al Marketplace"
    >
      <p>
        Puedes volver al marketplace cuando quieras. Si completaste un pago
        antes de salir, revisa tu correo para ver tu orden.
      </p>
    </PageIntro>
  );
}
