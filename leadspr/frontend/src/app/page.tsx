import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  HeartHandshake,
  ShieldCheck,
  Sprout,
  Heart,
  Phone,
  Mail,
  MessageCircle,
  UsersRound,
} from "lucide-react";
import { company } from "@/lib/company";
import styles from "./home.module.css";

const services = [
  {
    Icon: ShieldCheck,
    title: "8 Seguros en 1",
    text: "Conoce cómo combinar distintas coberturas en una póliza y qué debes evaluar antes de elegirla.",
  },
  {
    Icon: Heart,
    title: "Seguro de Cáncer",
    text: "Orientación sobre protección económica ante un diagnóstico de cáncer y los gastos asociados al tratamiento.",
  },
  {
    Icon: HeartHandshake,
    title: "Gastos Finales",
    text: "Explora opciones de seguro de vida para ayudar a tu familia con los gastos que quedan tras un fallecimiento.",
  },
  {
    Icon: Sprout,
    title: "Retiro y Ahorro",
    text: "Conversa sobre tus metas de ahorro y las alternativas para complementar tus ingresos durante el retiro.",
  },
];

export default function HomePage() {
  return (
    <div className={styles.home}>
      <section
        className={`container ${styles.hero}`}
        aria-labelledby="hero-title"
      >
        <div className={styles.heroCopy}>
          <p className="eyebrow">FSG Seguros · Puerto Rico</p>
          <h1 id="hero-title">
            Tu familia. Tu futuro.
            <br />
            <em>Vamos a protegerlos.</em>
          </h1>
          <p className={styles.description}>
            Entender tu seguro es el primer paso. En FSG te orientamos sobre tus
            opciones, aclaramos tus dudas y te acompañamos al momento de una
            reclamación.
          </p>
          <div className={styles.actions}>
            <a href="#contacto" className="button button-primary">
              Solicita orientación gratis{" "}
              <ArrowRight size={17} aria-hidden="true" />
            </a>
            <a href="#servicios" className={styles.textLink}>
              Conoce los seguros <ArrowUpRight size={17} aria-hidden="true" />
            </a>
          </div>
          <p className={styles.heroNote}>
            Una conversación sin costo y sin compromiso.
          </p>
        </div>
        <figure className={styles.heroFigure}>
          <Image
            src="/images/fsg/equipo-fsg.jpg"
            alt="Seis integrantes del equipo de FSG juntos en un evento de la compañía."
            width={2048}
            height={1365}
            priority
            sizes="(max-width: 850px) 100vw, 55vw"
            className={styles.teamPhoto}
          />
          <figcaption>
            <span>Personas que te acompañan.</span>
            <span>Financial Support Group Inc.</span>
          </figcaption>
        </figure>
      </section>

      <section
        id="servicios"
        className={`container ${styles.services}`}
        aria-labelledby="services-title"
      >
        <div className={styles.sectionHeading}>
          <div>
            <p className="eyebrow">Seguros, retiro y ahorro</p>
            <h2 id="services-title">
              Decisiones de hoy.
              <br />
              Tranquilidad para lo que viene.
            </h2>
          </div>
          <p>
            Comenzamos por escucharte. Luego te explicamos las opciones de
            protección que puedes considerar para tu familia y tus planes.
          </p>
        </div>
        <div className={styles.serviceGrid}>
          {services.map(({ Icon, title, text }, index) => (
            <article className={styles.service} key={title}>
              <div className={styles.serviceTop}>
                <Icon size={26} strokeWidth={1.5} aria-hidden="true" />
                <span aria-hidden="true">0{index + 1}</span>
              </div>
              <h3>{title}</h3>
              <p>{text}</p>
              <a
                href="#contacto"
                aria-label={`Solicita orientación sobre ${title}`}
              >
                Quiero orientación <ArrowUpRight size={16} aria-hidden="true" />
              </a>
            </article>
          ))}
        </div>
      </section>

      <section
        className={`container ${styles.about}`}
        aria-labelledby="about-title"
      >
        <figure className={styles.aboutFigure}>
          <Image
            src="/images/fsg/equipo-certificaciones.jpeg"
            alt="Equipo de FSG con certificados. La imagen expresa: Más que una agencia, construimos historias de éxito."
            width={1080}
            height={1098}
            sizes="(max-width: 700px) 90vw, 35vw"
          />
        </figure>
        <div className={styles.aboutCopy}>
          <p className="eyebrow">Conoce a FSG</p>
          <h2 id="about-title">
            Detrás de tu póliza,
            <br />
            hay un equipo contigo.
          </h2>
          <p>
            Somos Financial Support Group Inc., FSG Seguros. Desde Puerto Rico,
            orientamos a familias, profesionales y negocios para que puedan
            entender su protección y tomar decisiones informadas.
          </p>
          <ul>
            <li>
              <strong>Opciones explicadas con claridad.</strong>
              <span>
                Trabajamos con múltiples aseguradoras para ayudarte a evaluar
                alternativas.
              </span>
            </li>
            <li>
              <strong>Orientación personal.</strong>
              <span>Tu necesidad y tus preguntas son el punto de partida.</span>
            </li>
            <li>
              <strong>Apoyo en la reclamación.</strong>
              <span>Te acompañamos con la radicación y el seguimiento.</span>
            </li>
          </ul>
          <a href="#contacto" className={styles.textLink}>
            Hablemos de lo que necesitas{" "}
            <ArrowUpRight size={17} aria-hidden="true" />
          </a>
        </div>
      </section>

      <section
        className={`container ${styles.agentSection}`}
        aria-labelledby="agents-title"
      >
        <UsersRound size={32} strokeWidth={1.4} aria-hidden="true" />
        <div>
          <p className="eyebrow">Espacio para profesionales de seguros</p>
          <h2 id="agents-title">Marketplace de Leads para Agentes</h2>
          <p>
            Consulta prospectos de seguro de vida por municipio, antigüedad y
            cantidad. Un espacio de FSG para la gestión comercial de agentes.
          </p>
        </div>
        <Link href="/leads" className="button button-primary">
          Ver Leads Disponibles <ArrowRight size={17} aria-hidden="true" />
        </Link>
      </section>

      <section
        id="contacto"
        className={`container ${styles.contact}`}
        aria-labelledby="contact-title"
      >
        <div>
          <p className="eyebrow">Estamos para orientarte</p>
          <h2 id="contact-title">Hablemos de tu próximo paso.</h2>
          <p>
            Comunícate con nuestro equipo para coordinar tu orientación
            gratuita.
          </p>
          <address>
            {company.address}
            <br />
            <span>{company.hours}</span>
          </address>
        </div>
        <div className={styles.contactLinks}>
          <a href={company.phoneHref}>
            <Phone size={21} aria-hidden="true" />
            <span>
              <small>Llámanos</small>
              {company.phone}
            </span>
            <ArrowUpRight size={18} aria-hidden="true" />
          </a>
          <a href={company.whatsapp} target="_blank" rel="noopener noreferrer">
            <MessageCircle size={21} aria-hidden="true" />
            <span>
              <small>Escríbenos por WhatsApp</small>787-233-4871
            </span>
            <ArrowUpRight size={18} aria-hidden="true" />
          </a>
          <a href={`mailto:${company.email}`}>
            <Mail size={21} aria-hidden="true" />
            <span>
              <small>Correo electrónico</small>
              {company.email}
            </span>
            <ArrowUpRight size={18} aria-hidden="true" />
          </a>
        </div>
      </section>
    </div>
  );
}
