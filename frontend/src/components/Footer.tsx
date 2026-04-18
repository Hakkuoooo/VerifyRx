import Link from "next/link";

// Three-column footer — the pattern every UK public/health service uses.
// External safety links open in a new tab with rel=noopener so they can't
// hijack the opener.
const external = (href: string) => ({
  href,
  target: "_blank",
  rel: "noopener noreferrer",
});

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-[var(--color-line-strong)] mt-16">
      <div className="max-w-6xl mx-auto px-4 py-10 grid grid-cols-1 md:grid-cols-3 gap-10 text-sm">
        {/* Service column */}
        <div>
          <div className="font-semibold text-[var(--color-ink)] mb-3">
            VerifyRX UK
          </div>
          <p className="text-[var(--color-ink-muted)] leading-relaxed">
            Spot fake pharmacy websites, scam texts and counterfeit
            packaging before they reach you or someone you care for.
          </p>
          <p className="text-[var(--color-ink-faint)] text-xs mt-4 leading-relaxed">
            VerifyRX gives a risk indication, not medical advice. If you
            have taken a medicine you suspect is counterfeit, call{" "}
            <a {...external("https://111.nhs.uk/")} className="prose-link">
              NHS&nbsp;111
            </a>{" "}
            or contact your GP.
          </p>
        </div>

        {/* Safety resources — all external, authoritative UK bodies. */}
        <div>
          <div className="font-semibold text-[var(--color-ink)] mb-3">
            Safety resources
          </div>
          <ul className="space-y-2">
            <li>
              <a
                {...external("https://www.pharmacyregulation.org/registers")}
                className="prose-link"
              >
                GPhC register — check a pharmacy
              </a>
            </li>
            <li>
              <a
                {...external("https://yellowcard.mhra.gov.uk/")}
                className="prose-link"
              >
                MHRA Yellow Card — report a suspect medicine
              </a>
            </li>
            <li>
              <a
                {...external("https://www.actionfraud.police.uk/")}
                className="prose-link"
              >
                Action Fraud — report a scam
              </a>
            </li>
            <li>
              <a
                {...external("https://www.nhs.uk/nhs-services/pharmacies/")}
                className="prose-link"
              >
                NHS — find a local pharmacy
              </a>
            </li>
          </ul>
        </div>

        {/* About & legal */}
        <div>
          <div className="font-semibold text-[var(--color-ink)] mb-3">
            About
          </div>
          <ul className="space-y-2">
            <li>
              <Link href="/results" className="prose-link">
                Methodology &amp; evaluation
              </Link>
            </li>
            <li>
              <Link href="/dashboard" className="prose-link">
                My checks
              </Link>
            </li>
            <li>
              <a href="#" className="prose-link">
                Privacy
              </a>
            </li>
            <li>
              <a href="#" className="prose-link">
                Accessibility
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-[var(--color-line)]">
        <div className="max-w-6xl mx-auto px-4 py-4 text-xs text-[var(--color-ink-faint)] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <span>© {year} VerifyRX UK. All rights reserved.</span>
          <span>
            Data from the GPhC register, VirusTotal and MHRA.
          </span>
        </div>
      </div>
    </footer>
  );
}
