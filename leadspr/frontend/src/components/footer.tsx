import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { Brand } from "@/components/brand";

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-main">
          <div>
            <Brand />
            <p>Cobertura para Hoy. Protección para Mañana.</p>
          </div>
          <div className="footer-links">
            <Link href="/">Inicio</Link>
            <Link href="/leads">Leads para Agentes</Link>
            <Link href="/admin">Administración</Link>
          </div>
          <div className="footer-note">
            <ShieldCheck size={20} aria-hidden="true" />
            <span>
              Por las familias.
              <br />
              Por el futuro. Por Puerto Rico.
            </span>
          </div>
        </div>
        <div className="footer-bottom">
          <span>
            © {new Date().getFullYear()} Borinquen Life &amp; Protection
          </span>
          <span>
            Ambiente de demostración — todos los leads y las transacciones
            mostradas son simulados.
          </span>
        </div>
      </div>
    </footer>
  );
}
