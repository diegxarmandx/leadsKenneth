"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, MapPin } from "lucide-react";
import { Brand } from "@/components/brand";

const links = [
  { href: "/", label: "Inicio" },
  { href: "/leads", label: "Leads para Agentes" },
  { href: "/admin", label: "Administración" },
];

export function Navbar() {
  const pathname = usePathname();
  return (
    <>
      <div className="brand-bar">
        <div className="container">
          <span>
            <MapPin size={12} aria-hidden="true" /> De Puerto Rico. Pensando en
            ti.
          </span>
          <span className="brand-bar-tagline">
            Cobertura para Hoy. Protección para Mañana.
          </span>
        </div>
      </div>
      <header className="site-header">
        <div className="container nav-inner">
          <Brand />
          <nav aria-label="Navegación principal">
            {links.map(({ href, label }) => {
              const current =
                href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(href) ||
                    (href === "/leads" && pathname.startsWith("/checkout"));
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={current ? "page" : undefined}
                  className={current ? "nav-link active" : "nav-link"}
                >
                  {label}
                  {href === "/admin" && (
                    <ArrowUpRight size={13} aria-hidden="true" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
    </>
  );
}
