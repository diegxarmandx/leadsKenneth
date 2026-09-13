import Link from "next/link";

type PageIntroProps = {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  href?: string;
  linkLabel?: string;
};

export function PageIntro({
  eyebrow,
  title,
  children,
  href = "/",
  linkLabel = "Volver al inicio",
}: PageIntroProps) {
  return (
    <section className="container page-intro">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <div className="page-intro-copy">{children}</div>
      <Link href={href} className="button button-primary">
        {linkLabel}{" "}
        <span aria-hidden="true" className="ml-3">
          →
        </span>
      </Link>
    </section>
  );
}
