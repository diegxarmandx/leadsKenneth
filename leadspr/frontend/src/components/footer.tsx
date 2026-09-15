import Link from "next/link";
import { company } from "@/lib/company";

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-main">
          <div>
            <Link
              href="/"
              className="footer-brand"
              aria-label={`${company.name} — Inicio`}
            >
              <span className="footer-brand-name">{company.name}</span>
              <span className="footer-brand-description">
                {company.legalName}
              </span>
            </Link>
            <p>Orientación en seguros para tu familia y tu futuro.</p>
          </div>
          <div className="footer-links">
            <Link href="/">Inicio</Link>
            <Link href="/leads">Leads para Agentes</Link>
            <Link href="/admin">Administración</Link>
          </div>
          <address className="footer-contact">
            <a href={company.phoneHref}>{company.phone}</a>
            <a href={`mailto:${company.email}`}>{company.email}</a>
            <div className="footer-social">
              <a
                href={company.facebook}
                target="_blank"
                rel="noopener noreferrer"
              >
                Facebook
              </a>
              <a
                href={company.instagram}
                target="_blank"
                rel="noopener noreferrer"
              >
                Instagram
              </a>
            </div>
          </address>
        </div>
        <div className="footer-bottom">
          <span>
            © {new Date().getFullYear()} {company.legalName}
          </span>
          <span>Marketplace en modo demo: leads y pagos de prueba.</span>
        </div>
      </div>
    </footer>
  );
}
