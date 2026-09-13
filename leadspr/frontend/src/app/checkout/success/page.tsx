import type { Metadata } from "next";
import { PageIntro } from "@/components/page-intro";

export const metadata: Metadata = { title: "Checkout returned", robots: { index: false, follow: false } };

export default function SuccessPage() {
  return (
    <PageIntro eyebrow="Checkout" title="Thanks for visiting LeadsPR.">
      <p>Order status will appear here once the buyer flow is connected. This page does not confirm payment. Purchased leads are sent by email after payment and allocation are confirmed.</p>
    </PageIntro>
  );
}
