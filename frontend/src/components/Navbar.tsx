import { useState } from "react";
import Button from "./Button";

const navLinks = [
  { label: "Shop", href: "#" },
  { label: "Categories", href: "#" },
  { label: "Sell on Meraki", href: "#" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-canvas/95 backdrop-blur">
      <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-5 md:px-8">
        <a href="/" className="font-display text-2xl font-medium tracking-tight text-ink">
          Meraki
        </a>

        <nav className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm font-medium text-ink/80 transition-colors hover:text-ink"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <Button variant="secondary" className="px-5 py-2.5">
            Log in
          </Button>
          <Button variant="primary" className="px-5 py-2.5">
            Sign up
          </Button>
        </div>

        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-line md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen(!open)}
        >
          {open ? (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path
                d="M1 1L17 17M17 1L1 17"
                stroke="#1C1A17"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
          ) : (
            <svg width="18" height="14" viewBox="0 0 18 14" fill="none" aria-hidden="true">
              <path
                d="M0 1H18M0 7H18M0 13H18"
                stroke="#1C1A17"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
          )}
        </button>
      </div>

      {open && (
        <div className="border-t border-line px-5 pb-6 pt-2 md:hidden">
          <nav className="flex flex-col gap-1">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="rounded-xl px-3 py-3 text-base font-medium text-ink hover:bg-white"
                onClick={() => setOpen(false)}
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="mt-4 flex flex-col gap-3">
            <Button variant="secondary" className="w-full">
              Log in
            </Button>
            <Button variant="primary" className="w-full">
              Sign up
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}
