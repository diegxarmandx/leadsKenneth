import Link from "next/link";

type PageIntroProps = {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  href?: string;
  linkLabel?: string;
};

export function PageIntro({ eyebrow, title, children, href = "/", linkLabel = "Back to home" }: PageIntroProps) {
  return (
    <section className="max-w-2xl">
      <p className="mb-5 text-sm font-semibold tracking-widest uppercase text-green-800">{eyebrow}</p>
      <h1 className="text-4xl leading-tight font-semibold tracking-tight sm:text-6xl">{title}</h1>
      <div className="mt-6 max-w-xl text-lg leading-relaxed text-foreground/75">{children}</div>
      <Link href={href} className="mt-9 inline-flex rounded-md bg-foreground px-5 py-3 text-sm font-medium text-white hover:bg-green-900">
        {linkLabel} <span aria-hidden="true" className="ml-3">→</span>
      </Link>
    </section>
  );
}
