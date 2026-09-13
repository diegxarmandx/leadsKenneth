import type { Metadata } from "next";
import { PageIntro } from "@/components/page-intro";

export const metadata: Metadata = { title: "Checkout closed", robots: { index: false, follow: false } };

export default function CancelPage() {
  return (
    <PageIntro eyebrow="Checkout" title="You’ve left checkout." href="/buy" linkLabel="Return to buy leads">
      <p>You can return to the buyer page whenever you’re ready. If you completed a payment before leaving, check your email for your order.</p>
    </PageIntro>
  );
}
