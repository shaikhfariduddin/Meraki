import Button from "./Button";

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div
        className="absolute inset-0 bg-grid opacity-60 [background-size:40px_40px]"
        style={{ maskImage: "linear-gradient(to bottom, black, transparent)" }}
        aria-hidden="true"
      />
      <div className="relative mx-auto max-w-4xl px-5 py-24 text-center md:py-32">
        <p className="text-sm font-medium text-muted">
          A marketplace built by independent sellers
        </p>
        <h1 className="mt-6 font-display text-4xl font-medium leading-[1.1] text-ink md:text-6xl">
          Everything here is made with <span className="text-accent">meraki</span> — a little
          bit of soul in every listing.
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg text-muted">
          Discover products from independent sellers who put real care into what they make —
          browse, compare, and buy from people, not warehouses.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button variant="primary" className="w-full px-8 py-3.5 text-base sm:w-auto">
            Start shopping
          </Button>
          <Button variant="secondary" className="w-full px-8 py-3.5 text-base sm:w-auto">
            Become a seller
          </Button>
        </div>
      </div>
    </section>
  );
}
