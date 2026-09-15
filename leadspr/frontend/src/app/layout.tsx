import type { Metadata } from "next";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";
import { company } from "@/lib/company";
import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/latin-500.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/manrope/latin-800.css";
import "@fontsource/libre-baskerville/latin-400.css";
import "@fontsource/libre-baskerville/latin-400-italic.css";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "FSG Seguros — Asesoría en seguros en Puerto Rico",
    template: "%s | FSG Seguros",
  },
  description: company.description,
  applicationName: company.name,
  icons: {
    icon: { url: "/images/fsg/logo-fsg.jpg", type: "image/jpeg" },
    apple: "/images/fsg/logo-fsg.jpg",
  },
  openGraph: {
    title: "FSG Seguros — Asesoría en seguros en Puerto Rico",
    description: company.description,
    siteName: company.name,
    locale: "es_PR",
    type: "website",
  },
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es-PR" data-scroll-behavior="smooth">
      <body>
        <a href="#main" className="skip-link">
          Saltar al contenido
        </a>
        <Navbar />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
