import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "LeadsPR", template: "%s | LeadsPR" },
  description: "Life insurance leads for insurance professionals in Puerto Rico.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:bg-white focus:p-3">
          Skip to content
        </a>
        <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 sm:px-10">
          <header className="flex flex-wrap items-center justify-between gap-6 border-b border-foreground/15 py-7">
            <Link href="/" className="text-xl font-bold tracking-tight">LeadsPR<span className="text-green-700">.</span></Link>
            <nav aria-label="Main navigation" className="flex gap-6 text-sm">
              <Link href="/buy" className="hover:underline">Buy leads</Link>
              <Link href="/admin" className="hover:underline">Admin</Link>
            </nav>
          </header>
          <main id="main" className="flex flex-1 flex-col justify-center py-20">{children}</main>
          <footer className="border-t border-foreground/15 py-6 text-sm text-foreground/70">
            LeadsPR · Puerto Rico
          </footer>
        </div>
      </body>
    </html>
  );
}
