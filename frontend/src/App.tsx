import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import CategoryCard from "./components/CategoryCard";

const categories = [
  { name: "Home & Living", description: "Handmade decor, textiles, and small-batch goods." },
  { name: "Apparel", description: "Independent clothing labels and accessories." },
  { name: "Art & Prints", description: "Original art, prints, and illustration." },
  { name: "Craft Supplies", description: "Materials and tools from specialty makers." },
];

function App() {
  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />
      <Hero />
      <section className="mx-auto max-w-6xl px-5 py-20 md:px-8">
        <h2 className="font-display text-3xl font-medium text-ink md:text-4xl">
          Shop by category
        </h2>
        <p className="mt-3 max-w-xl text-muted">
          A few of the categories independent sellers list on Meraki.
        </p>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {categories.map((category) => (
            <CategoryCard
              key={category.name}
              name={category.name}
              description={category.description}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

export default App;
