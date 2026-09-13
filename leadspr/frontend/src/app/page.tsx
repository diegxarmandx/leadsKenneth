import { PageIntro } from "@/components/page-intro";

export default function HomePage() {
  return (
    <PageIntro eyebrow="Life insurance · Puerto Rico" title="Your next conversation starts here." href="/buy" linkLabel="Explore LeadsPR">
      <p>Life insurance leads for professionals serving Puerto Rico. Choose your municipality, price tier, and quantity. Receive your assigned leads by email.</p>
      <p className="mt-4 text-sm">The buyer experience is in development. Online purchasing will be available here soon.</p>
    </PageIntro>
  );
}
