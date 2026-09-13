import type { Metadata } from "next";
import { PageIntro } from "@/components/page-intro";

export const metadata: Metadata = { title: "Buy leads" };

export default function BuyPage() {
  return (
    <PageIntro eyebrow="Buy leads" title="Find your next opportunity.">
      <p>The buyer flow is coming soon. You’ll be able to choose a municipality, an exact price tier, and the number of leads you need.</p>
    </PageIntro>
  );
}
