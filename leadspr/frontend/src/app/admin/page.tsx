import type { Metadata } from "next";
import { PageIntro } from "@/components/page-intro";

export const metadata: Metadata = { title: "Admin", robots: { index: false, follow: false } };

export default function AdminPage() {
  return (
    <PageIntro eyebrow="Administration" title="Your workspace is on its way.">
      <p>The admin dashboard and sign-in experience are in development. This page contains no administrative data.</p>
    </PageIntro>
  );
}
