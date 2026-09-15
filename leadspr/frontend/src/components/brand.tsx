import Link from "next/link";
import Image from "next/image";
import { company } from "@/lib/company";

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link
      href="/"
      className={`brand ${light ? "brand-light" : ""}`}
      aria-label={`${company.name} — Inicio`}
    >
      <Image
        src="/images/fsg/logo-fsg.jpg"
        alt={`${company.name} — ${company.legalName}`}
        width={960}
        height={960}
        sizes="(max-width: 600px) 160px, 180px"
        className="brand-logo"
      />
    </Link>
  );
}
