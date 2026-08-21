import type { QueueItem } from "../api/types";
import { money } from "../lib/format";

type Props = {
  items: QueueItem[];
  activeId?: string;
  onSelect: (id: string) => void;
  sheet?: boolean;
  open?: boolean;
  onToggle?: () => void;
  note?: string;
};

export function Queue({ items, activeId, onSelect, sheet, open, onToggle, note }: Props) {
  const live = items.length;

  return (
    <aside className={`queue${sheet ? " queue--sheet" : ""}${open ? " is-open" : ""}`}>
      <header className="queue__head">
        {sheet ? (
          <button type="button" className="queue__peek" onClick={onToggle}>
            {live} en cola
          </button>
        ) : (
          <>
            <p className="queue__brand">Cuadre IQ</p>
            <p className="queue__count">{live} en cola</p>
          </>
        )}
      </header>
      <ul className="queue__list">
        {items.map((item) => {
          const mark = item.status === "needs_review" || item.status === "error";
          return (
            <li key={item.id}>
              <button
                type="button"
                className={`queue__item${item.id === activeId ? " is-active" : ""}`}
                onClick={() => onSelect(item.id)}
              >
                <span className="queue__name">
                  <span>{item.supplier || item.filename}</span>
                  {mark ? <i className="queue__mark" aria-hidden="true" /> : null}
                </span>
                <span className="queue__meta">
                  <span>{item.number || item.status}</span>
                  <span>{money(item.total)}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {note && !sheet ? <p className="queue__note">{note}</p> : null}
    </aside>
  );
}
