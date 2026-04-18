"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";

// Nav labels are transactional ("Check a website"), not feature names
// ("URL Checker"). Matches how NHS.uk labels its top-level services.
const navLinks = [
  { href: "/url-checker", label: "Check a website" },
  { href: "/sms-checker", label: "Check a text message" },
  { href: "/image-checker", label: "Check packaging" },
  { href: "/dashboard", label: "My checks" },
];

export default function Header() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="bg-[var(--color-primary)] text-white sticky top-0 z-50 shadow-[0_1px_0_rgba(0,0,0,0.1)]">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-baseline gap-2 group"
          aria-label="VerifyRX UK — home"
        >
          <span className="text-[17px] font-semibold tracking-tight">
            VerifyRX
          </span>
          <span className="text-[11px] font-medium uppercase tracking-[0.12em] opacity-80">
            UK
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-0" aria-label="Main">
          {navLinks.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3.5 h-14 flex items-center text-sm font-medium border-b-2 transition-colors ${
                  active
                    ? "border-white text-white"
                    : "border-transparent text-white/80 hover:text-white hover:border-white/40"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 -mr-2 rounded hover:bg-white/10"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <nav
          className="md:hidden border-t border-white/15 bg-[var(--color-primary)]"
          aria-label="Main"
        >
          {navLinks.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className={`block px-4 py-3 text-sm font-medium border-l-2 ${
                  active
                    ? "border-white bg-white/10"
                    : "border-transparent text-white/85 hover:bg-white/5"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      )}
    </header>
  );
}
