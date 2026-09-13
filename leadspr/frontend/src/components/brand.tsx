import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link
      href="/"
      className={`brand ${light ? "brand-light" : ""}`}
      aria-label="Borinquen Life & Protection — Inicio"
    >
      <span className="brand-mark">
        <ShieldCheck aria-hidden="true" strokeWidth={1.4} />
      </span>
      <span>
        <span className="brand-name">Borinquen</span>
        <span className="brand-descriptor">Life &amp; Protection</span>
      </span>
    </Link>
  );
}
