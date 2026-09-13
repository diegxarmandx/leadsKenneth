import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  HeartHandshake,
  MapPin,
  ShieldCheck,
  UsersRound,
  Sprout,
} from "lucide-react";

export default function HomePage() {
  return (
    <>
      <section className="home-hero container">
        <div className="hero-copy">
          <p className="eyebrow">
            <span />
            Protección de aquí, para tu vida.
          </p>
          <h1>
            Protegiendo a las familias de <em>Puerto Rico</em> para lo que viene
          </h1>
          <p className="hero-description">
            Soluciones de seguro de vida diseñadas para las necesidades de las
            familias en Puerto Rico.
          </p>
          <div className="hero-actions">
            <Link href="/leads" className="button button-primary">
              Explorar Leads para Agentes{" "}
              <ArrowRight size={17} aria-hidden="true" />
            </Link>
            <a href="#our-promise" className="button button-text">
              Conoce Más <ArrowUpRight size={16} aria-hidden="true" />
            </a>
          </div>
          <div className="hero-reassurance">
            <ShieldCheck size={19} aria-hidden="true" />
            <span>Conocimiento local. Tranquilidad duradera.</span>
          </div>
        </div>
        <div className="hero-visual">
          <Image
            src="/images/family.jpg"
            alt="Una familia disfruta de un paseo al aire libre."
            fill
            priority
            sizes="(max-width: 760px) 100vw, 48vw"
            className="hero-photo"
          />
          <div className="photo-label">
            <span className="photo-label-icon">
              <HeartHandshake size={25} strokeWidth={1.5} aria-hidden="true" />
            </span>
            <div>
              <strong>Contigo en cada etapa.</strong>
              <span>Protege lo que más importa.</span>
            </div>
          </div>
          <span className="photo-corner" aria-hidden="true" />
        </div>
      </section>
      <section id="our-promise" className="value-section container">
        <div className="value-heading">
          <p className="eyebrow">Nuestro compromiso</p>
          <h2>Protección que toma en cuenta tu vida.</h2>
        </div>
        <div className="value-grid">
          {[
            {
              Icon: HeartHandshake,
              title: "Protección Familiar",
              text: "Coberturas diseñadas para ayudar a las familias a proteger sus ingresos, sus seres queridos y sus planes a largo plazo.",
            },
            {
              Icon: MapPin,
              title: "Enfocados en Puerto Rico",
              text: "Sirviendo comunidades alrededor de toda la isla con conocimiento del mercado local.",
            },
            {
              Icon: Sprout,
              title: "Crecimiento para Agentes",
              text: "Nuestro marketplace de leads ayuda a profesionales de seguros a conectar con prospectos disponibles.",
            },
          ].map(({ Icon, title, text }) => (
            <article className="value-card" key={title}>
              <span className="value-icon">
                <Icon size={24} strokeWidth={1.5} aria-hidden="true" />
              </span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="container marketplace-intro">
        <div className="marketplace-intro-icon">
          <UsersRound size={35} strokeWidth={1.3} aria-hidden="true" />
        </div>
        <div>
          <p className="eyebrow">Para profesionales de seguros</p>
          <h2>Leads de Seguro de Vida para Agentes</h2>
          <p>
            Accede a prospectos disponibles de seguro de vida según municipio,
            antigüedad del lead y cantidad.
          </p>
        </div>
        <Link href="/leads" className="button button-primary">
          Ver Leads Disponibles <ArrowRight size={17} aria-hidden="true" />
        </Link>
      </section>
    </>
  );
}
