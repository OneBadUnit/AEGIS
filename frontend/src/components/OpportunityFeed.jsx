// frontend/src/components/OpportunityFeed.jsx

import OpportunityCard from "./OpportunityCard";


export default function OpportunityFeed({
  items = [],
  selected,
  onSelect,
}) {
  if (!items.length) {
    return (
      <div className="opportunity-feed empty">
        No opportunities to display.
      </div>
    );
  }

  return (
    <div className="opportunity-feed">
      {items.map((item) => {
        const key = item.id || item.url || item.title;

        const isSelected =
          selected &&
          (selected.id === item.id || selected.url === item.url);

        return (
          <OpportunityCard
            key={key}
            item={item}
            isSelected={isSelected}
            onClick={() => onSelect?.(item)}
          />
        );
      })}
    </div>
  );
}