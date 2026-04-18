import Link from "next/link";
import { ArrowRight } from "lucide-react";

// Landing is deliberately content-dense and left-aligned — the marketing
// hero pattern (gradient bg, centered H1, emoji icons) reads as generic
// SaaS. Real UK health services lead with what the user can do, cite a
// source for every claim, and save decoration for later.

const services = [
  {
    href: "/url-checker",
    eyebrow: "Website",
    title: "Check a pharmacy website",
    body: "Cross-check a .co.uk or international pharmacy URL against the General Pharmaceutical Council register, HTTPS, domain age and known-malicious indicators.",
    cta: "Check a website",
  },
  {
    href: "/sms-checker",
    eyebrow: "Text message",
    title: "Check a suspicious text",
    body: "Paste a text you've received from “your GP”, “the NHS” or an online pharmacy. Our model flags the exact phrases that match known scam patterns.",
    cta: "Check a text message",
  },
  {
    href: "/image-checker",
    eyebrow: "Packaging",
    title: "Check medicine packaging",
    body: "Upload a photo of a pack you're unsure about. We compare font, print quality, barcode region and batch-code area against authentic reference packaging.",
    cta: "Check packaging",
  },
];

// Each stat includes a source — claims without citations are what AI
// demos do, and examiners/users both notice immediately.
const stats = [
  {
    figure: "95%",
    label:
      "of online pharmacies are operating illegally, out of ~35,000 audited",
    source: "NABP, Rogue Pharmacy Report 2023",
  },
  {
    figure: "1 in 10",
    label:
      "medical products in low- and middle-income countries is falsified or substandard",
    source: "World Health Organization, 2017",
  },
  {
    figure: "£28m",
    label: "of fake medicines seized in a single UK operation (Pangea XIV)",
    source: "MHRA, 2021",
  },
];

const steps = [
  {
    n: "01",
    title: "Submit",
    body: "Paste a URL, a text message, or upload a pack image. Nothing is stored after the check completes.",
  },
  {
    n: "02",
    title: "Verify",
    body: "Signals from the GPhC register, VirusTotal, WHOIS and trained machine-learning models are combined into a single risk score.",
  },
  {
    n: "03",
    title: "Decide",
    body: "You get a clear red / amber / green rating and the exact reasons behind it — no black box.",
  },
];

export default function Home() {
  return (
    <div>
      {/* ─── Hero ─── */}
      <section className="bg-white border-b border-[var(--color-line)]">
        <div className="max-w-6xl mx-auto px-4 py-16 md:py-24 grid md:grid-cols-12 gap-10">
          <div className="md:col-span-8">
            <p className="text-sm font-medium text-[var(--color-primary)] tracking-wide uppercase">
              Medicine safety — UK
            </p>
            <h1 className="display mt-3 text-[40px] md:text-[56px] font-semibold text-[var(--color-ink)]">
              Check before you buy.
            </h1>
            <p className="mt-5 text-lg md:text-xl text-[var(--color-ink-muted)] max-w-2xl leading-relaxed">
              Spot fake pharmacy websites, scam texts and counterfeit
              packaging before they reach your doorstep — in seconds, with
              the reasons shown plainly.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
              <Link
                href="/url-checker"
                className="inline-flex items-center justify-center h-12 px-5 bg-[var(--color-action)] hover:bg-[var(--color-action-hover)] text-white text-[15px] font-semibold rounded-[2px] transition-colors"
              >
                Check a website
                <ArrowRight className="w-4 h-4 ml-2" aria-hidden />
              </Link>
              <Link
                href="/sms-checker"
                className="text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] font-medium text-[15px] underline underline-offset-4"
              >
                Or check a text message
              </Link>
            </div>

            <p className="mt-8 text-[13px] text-[var(--color-ink-faint)]">
              Free to use. Nothing you submit is stored.
            </p>
          </div>
        </div>
      </section>

      {/* ─── Stats ─── */}
      <section className="bg-[var(--color-primary-light)] border-b border-[var(--color-primary-border)]">
        <div className="max-w-6xl mx-auto px-4 py-10 grid grid-cols-1 md:grid-cols-3 gap-8">
          {stats.map((s) => (
            <div key={s.label}>
              <div className="text-4xl font-semibold text-[var(--color-primary)] tracking-tight">
                {s.figure}
              </div>
              <p className="mt-2 text-[15px] text-[var(--color-ink)] leading-snug">
                {s.label}
              </p>
              <p className="mt-2 text-xs text-[var(--color-ink-faint)]">
                Source: {s.source}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Services ─── */}
      <section className="py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="max-w-3xl mb-10">
            <h2 className="text-2xl md:text-3xl font-semibold text-[var(--color-ink)] tracking-tight">
              What you can check
            </h2>
            <p className="mt-2 text-[var(--color-ink-muted)]">
              Three entry points covering the routes counterfeit medicines
              most often reach consumers in the UK.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {services.map((s) => (
              <Link
                key={s.href}
                href={s.href}
                className="group block bg-white border border-[var(--color-line)] border-l-[3px] border-l-[var(--color-primary)] p-6 hover:border-[var(--color-primary-border)] hover:border-l-[var(--color-primary)] transition-colors"
              >
                <div className="text-[11px] uppercase tracking-[0.1em] text-[var(--color-ink-faint)] font-semibold">
                  {s.eyebrow}
                </div>
                <h3 className="mt-2 text-lg font-semibold text-[var(--color-ink)]">
                  {s.title}
                </h3>
                <p className="mt-2 text-[14px] text-[var(--color-ink-muted)] leading-relaxed">
                  {s.body}
                </p>
                <div className="mt-5 inline-flex items-center text-[var(--color-primary)] font-medium text-sm group-hover:text-[var(--color-primary-hover)]">
                  {s.cta}
                  <ArrowRight
                    className="w-4 h-4 ml-1.5 transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ─── How it works ─── */}
      <section className="py-16 px-4 border-t border-[var(--color-line)] bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="max-w-3xl mb-10">
            <h2 className="text-2xl md:text-3xl font-semibold text-[var(--color-ink)] tracking-tight">
              How we check
            </h2>
            <p className="mt-2 text-[var(--color-ink-muted)]">
              Every check combines public-register lookups with
              machine-learning models trained on real scam messages and
              pack photographs.
            </p>
          </div>
          <ol className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((s) => (
              <li key={s.n} className="border-t-2 border-[var(--color-ink)] pt-5">
                <div className="text-sm font-semibold text-[var(--color-ink-faint)] tracking-wider">
                  {s.n}
                </div>
                <h3 className="mt-2 text-lg font-semibold text-[var(--color-ink)]">
                  {s.title}
                </h3>
                <p className="mt-2 text-[15px] text-[var(--color-ink-muted)] leading-relaxed">
                  {s.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ─── Safety disclaimer band ─── */}
      <section className="bg-[var(--color-warning-light)] border-y border-[color:rgba(138,75,0,0.25)]">
        <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col md:flex-row gap-4 md:items-center md:justify-between">
          <div className="max-w-3xl">
            <div className="text-[13px] font-semibold uppercase tracking-[0.1em] text-[var(--color-warning)]">
              Important
            </div>
            <p className="mt-1 text-[15px] text-[var(--color-ink)] leading-relaxed">
              VerifyRX gives a risk indication. It is not medical advice
              and cannot replace a pharmacist. If you have already taken a
              medicine you suspect is counterfeit, call{" "}
              <a
                href="https://111.nhs.uk/"
                target="_blank"
                rel="noopener noreferrer"
                className="prose-link"
              >
                NHS&nbsp;111
              </a>{" "}
              or contact your GP straight away.
            </p>
          </div>
          <a
            href="https://yellowcard.mhra.gov.uk/"
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 inline-flex items-center justify-center h-11 px-4 border border-[var(--color-ink)] text-[var(--color-ink)] text-sm font-semibold hover:bg-[var(--color-ink)] hover:text-white transition-colors"
          >
            Report a suspect medicine →
          </a>
        </div>
      </section>
    </div>
  );
}
