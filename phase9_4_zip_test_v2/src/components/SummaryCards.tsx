import type { Equipment } from "../types/equipment";

interface SummaryCardsProps {
  equipment: Equipment[];
}

interface SummaryCard {
  label: string;
  value: number;
  className: string;
}

export default function SummaryCards({
  equipment,
}: SummaryCardsProps): JSX.Element {
  const counts = equipment.reduce(
    (summary, item) => {
      summary[item.status] += 1;
      return summary;
    },
    {
      Available: 0,
      "In Use": 0,
      Maintenance: 0,
      Retired: 0,
    } as Record<Equipment["status"], number>,
  );

  const cards: SummaryCard[] = [
    {
      label: "Total equipment",
      value: equipment.length,
      className: "summary-card--total",
    },
    {
      label: "Available",
      value: counts.Available,
      className: "summary-card--available",
    },
    {
      label: "In use",
      value: counts["In Use"],
      className: "summary-card--in-use",
    },
    {
      label: "Maintenance",
      value: counts.Maintenance,
      className: "summary-card--maintenance",
    },
    {
      label: "Retired",
      value: counts.Retired,
      className: "summary-card--retired",
    },
  ];

  return (
    <section
      className="summary-cards"
      aria-label="Equipment inventory summary"
    >
      {cards.map((card) => (
        <article className={`summary-card ${card.className}`} key={card.label}>
          <div className="summary-card__content">
            <p className="summary-card__label">{card.label}</p>
            <p className="summary-card__value" aria-label={`${card.value}`}>
              {card.value}
            </p>
          </div>
        </article>
      ))}
    </section>
  );
}
