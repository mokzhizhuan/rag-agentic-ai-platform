import { useMemo } from "react";
import {
  EQUIPMENT_STATUSES,
  type Equipment,
  type EquipmentSortKey,
  type EquipmentStatus,
  type SortConfig,
} from "../types/equipment";

type StatusFilter = EquipmentStatus | "All";

interface EquipmentTableProps {
  equipment: Equipment[];
  searchQuery: string;
  onSearchChange: (value: string) => void;
  statusFilter: StatusFilter;
  onStatusFilterChange: (value: StatusFilter) => void;
  sortConfig: SortConfig;
  onSort: (key: EquipmentSortKey) => void;
  onEdit: (equipment: Equipment) => void;
  onDelete: (equipment: Equipment) => void;
}

const sortableColumns: Array<{
  key: EquipmentSortKey;
  label: string;
}> = [
  { key: "name", label: "Equipment" },
  { key: "category", label: "Category" },
  { key: "status", label: "Status" },
  { key: "location", label: "Location" },
  { key: "purchaseDate", label: "Purchase date" },
  { key: "assignedTo", label: "Assigned to" },
];

function getSortValue(item: Equipment, key: EquipmentSortKey): string {
  return item[key].toLocaleLowerCase();
}

function formatDate(date: string): string {
  if (!date) {
    return "—";
  }

  const parsedDate = new Date(`${date}T00:00:00`);

  if (Number.isNaN(parsedDate.getTime())) {
    return date;
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(parsedDate);
}

function statusClassName(status: EquipmentStatus): string {
  return `status-badge status-${status.toLowerCase().replace(/\s+/g, "-")}`;
}

export default function EquipmentTable({
  equipment,
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  sortConfig,
  onSort,
  onEdit,
  onDelete,
}: EquipmentTableProps) {
  const visibleEquipment = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase();

    return equipment
      .filter((item) => {
        if (statusFilter !== "All" && item.status !== statusFilter) {
          return false;
        }

        if (!query) {
          return true;
        }

        return [
          item.name,
          item.category,
          item.serialNumber,
          item.location,
          item.assignedTo,
          item.notes,
        ].some((value) => value.toLocaleLowerCase().includes(query));
      })
      .sort((first, second) => {
        const firstValue = getSortValue(first, sortConfig.key);
        const secondValue = getSortValue(second, sortConfig.key);
        const comparison = firstValue.localeCompare(secondValue, undefined, {
          numeric: true,
          sensitivity: "base",
        });

        return sortConfig.direction === "asc" ? comparison : -comparison;
      });
  }, [equipment, searchQuery, statusFilter, sortConfig]);

  const renderSortIndicator = (key: EquipmentSortKey) => {
    if (sortConfig.key !== key) {
      return <span className="sort-indicator" aria-hidden="true">↕</span>;
    }

    return (
      <span className="sort-indicator" aria-hidden="true">
        {sortConfig.direction === "asc" ? "↑" : "↓"}
      </span>
    );
  };

  return (
    <section className="equipment-section" aria-labelledby="equipment-list-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Inventory records</p>
          <h2 id="equipment-list-heading">Equipment</h2>
        </div>
        <p className="result-count" aria-live="polite">
          {visibleEquipment.length} of {equipment.length}{" "}
          {equipment.length === 1 ? "record" : "records"}
        </p>
      </div>

      <div className="table-controls">
        <div className="search-field">
          <label htmlFor="equipment-search">Search equipment</label>
          <input
            id="equipment-search"
            type="search"
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Name, serial number, location..."
          />
        </div>

        <div className="filter-field">
          <label htmlFor="status-filter">Filter by status</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(event) =>
              onStatusFilterChange(event.target.value as StatusFilter)
            }
          >
            <option value="All">All statuses</option>
            {EQUIPMENT_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
      </div>

      {visibleEquipment.length === 0 ? (
        <div className="empty-state" role="status">
          <h3>No equipment found</h3>
          <p>
            Try adjusting your search or status filter, or add a new equipment
            record.
          </p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="equipment-table">
            <caption className="visually-hidden">
              Equipment inventory records
            </caption>
            <thead>
              <tr>
                {sortableColumns.map(({ key, label }) => (
                  <th key={key} scope="col">
                    <button
                      type="button"
                      className="sort-button"
                      onClick={() => onSort(key)}
                      aria-label={`Sort by ${label}`}
                      aria-pressed={sortConfig.key === key}
                    >
                      {label}
                      {renderSortIndicator(key)}
                    </button>
                  </th>
                ))}
                <th scope="col">Serial number</th>
                <th scope="col" className="actions-column">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visibleEquipment.map((item) => (
                <tr key={item.id}>
                  <th scope="row">
                    <div className="equipment-name">{item.name}</div>
                    {item.notes && <div className="equipment-notes">{item.notes}</div>}
                  </th>
                  <td>{item.category}</td>
                  <td>
                    <span className={statusClassName(item.status)}>
                      {item.status}
                    </span>
                  </td>
                  <td>{item.location}</td>
                  <td>{formatDate(item.purchaseDate)}</td>
                  <td>{item.assignedTo || "Unassigned"}</td>
                  <td>
                    <code>{item.serialNumber}</code>
                  </td>
                  <td className="row-actions">
                    <button
                      type="button"
                      className="button button-small button-secondary"
                      onClick={() => onEdit(item)}
                      aria-label={`Edit ${item.name}`}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="button button-small button-danger"
                      onClick={() => onDelete(item)}
                      aria-label={`Delete ${item.name}`}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
