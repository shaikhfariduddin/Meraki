type CategoryCardProps = {
  name: string;
  description: string;
};

export default function CategoryCard({ name, description }: CategoryCardProps) {
  return (
    <div className="rounded-3xl border border-line bg-white p-6 shadow-soft transition-shadow hover:shadow-md">
      <h3 className="font-display text-xl font-medium text-ink">{name}</h3>
      <p className="mt-2 text-sm text-muted">{description}</p>
    </div>
  );
}
