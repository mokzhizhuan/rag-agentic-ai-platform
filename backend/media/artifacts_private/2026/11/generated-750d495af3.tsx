import React, { useMemo, useState } from "react";

type EquipmentStatus = "Online" | "Offline" | "Maintenance";

interface Equipment {
  id: string;
  name: string;
  status: EquipmentStatus;
  location: string;
  lastMaintenance: string;
  nextMaintenance: string;
}

type SortKey = keyof Equipment;
type SortDirection = "asc" | "desc";

const equipmentData: Equipment[] = [
  {
    id: "EQ-1001",
    name: "CNC Milling Machine",
    status: "Online",
    location: "Production Floor A",
    lastMaintenance: "2026-09-12",
    nextMaintenance: "2026-12-12",
  },
  {
    id: "EQ-1002",
    name: "Industrial Air Compressor",
    status: "Maintenance",
    location: "Utility Room",
    lastMaintenance: "2026-08-04",
    nextMaintenance: "2026-11-08",
  },
  {
    id: "EQ-1003",
    name: "Automated Assembly Robot",
    status: "Online",
    location: "Production Floor B",
    lastMaintenance: "2026-10-01",
    nextMaintenance: "2027-01-01",
  },
  {
    id: "EQ-1004",
    name: "Hydraulic Press",
    status: "Offline",
    location: "Production Floor A",
    lastMaintenance: "2026-07-19",
    nextMaintenance: "2026-11-19",
  },
  {
    id: "EQ-1005",
    name: "Conveyor System 04",
    status: "Online",
    location: "Shipping Area",
    lastMaintenance: "2026-09-25",
    nextMaintenance: "2026-12-25",
  },
  {
    id: "EQ-1006",
    name: "Laser Cutting Station",
    status: "Online",
    location: "Production Floor C",
    lastMaintenance: "2026-10-10",
    nextMaintenance: "2027-01-10",
  },
];

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));

const isMaintenanceDue = (equipment: Equipment) =>
  equipment.status === "Maintenance" ||
  new Date(`${equipment.nextMaintenance}T00:00:00`).getTime() <=
    new Date().setHours(0, 0, 0, 0);

function EquipmentDashboard() {
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<EquipmentStatus | "All">(
    "All"
  );
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [selectedEquipment, setSelectedEquipment] =
    useState<Equipment | null>(null);

  const rows = useMemo(() => {
    const query = searchText.trim().toLowerCase();

    return equipmentData
      .filter((equipment) => {
        const matchesSearch =
          !query ||
          equipment.name.toLowerCase().includes(query) ||
          equipment.id.toLowerCase().includes(query) ||
          equipment.location.toLowerCase().includes(query);
        const matchesStatus =
          statusFilter === "All" || equipment.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        const left = a[sortKey];
        const right = b[sortKey];
        const comparison = String(left).localeCompare(String(right), undefined, {
          numeric: true,
          sensitivity: "base",
        });
        return sortDirection === "asc" ? comparison : -comparison;
      });
  }, [searchText, statusFilter, sortKey, sortDirection]);

  const summary = useMemo(
    () => ({
      total: equipmentData.length,
      online: equipmentData.filter((item) => item.status === "Online").length,
      offline: equipmentData.filter((item) => item.status === "Offline").length,
      due: equipmentData.filter(isMaintenanceDue).length,
    }),
    []
  );

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((direction) => (direction === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const sortLabel = (key: SortKey) =>
    sortKey === key ? (sortDirection === "asc" ? " ↑" : " ↓") : "";

  return (
    <main className="dashboard">
      <style>{`
        * { box-sizing: border-box; }
        .dashboard {
          min-height: 100vh;
          padding: 32px;
          color: #172033;
          background: #f5f7fb;
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
        }
        .shell { max-width: 1240px; margin: 0 auto; }
        .heading { display: flex; justify-content: space-between; gap: 20px; align-items: flex-end; margin-bottom: 28px; }
        h1 { margin: 0 0 8px; font-size: clamp(1.8rem, 3vw, 2.5rem); letter-spacing: -0.04em; }
        .subtitle { margin: 0; color: #667085; }
        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
        .card, .panel { background: #fff; border: 1px solid #e4e8f0; border-radius: 14px; box-shadow: 0 5px 18px rgba(23,32,51,.04); }
        .card { padding: 20px; }
        .card-label { color: #667085; font-size: .88rem; }
        .card-value { margin-top: 8px; font-size: 1.85rem; font-weight: 750; }
        .controls { display: flex; gap: 12px; flex-wrap: wrap; padding: 18px; margin-bottom: 16px; }
        label { display: block; color: #475467; font-size: .82rem; font-weight: 650; }
        .control { flex: 1 1 240px; }
        input, select {
          width: 100%; margin-top: 7px; padding: 10px 12px; border: 1px solid #cbd3e1;
          border-radius: 8px; color: #172033; background: #fff; font: inherit;
        }
        input:focus, select:focus, button:focus-visible { outline: 3px solid #b9d3ff; outline-offset: 2px; border-color: #3878e8; }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; min-width: 760px; }
        th, td { padding: 15px 18px; text-align: left; border-bottom: 1px solid #edf0f5; }
        th { color: #667085; font-size: .76rem; letter-spacing: .04em; text-transform: uppercase; background: #fbfcfe; }
        th button { padding: 0; border: 0; color: inherit; background: transparent; font: inherit; font-weight: 700; cursor: pointer; }
        tbody tr { cursor: pointer; transition: background .15s ease; }
        tbody tr:hover, tbody tr[aria-selected="true"] { background: #f0f6ff; }
        .status { display: inline-flex; align-items: center; gap: 7px; font-weight: 650; }
        .dot { width: 9px; height: 9px; border-radius: 50%; background: currentColor; }
        .online { color: #16834b; } .offline { color: #c0392b; } .maintenance { color: #b87500; }
        .empty { padding: 42px 20px; text-align: center; color: #667085; }
        .details { margin-top: 18px; padding: 24px; }
        .details-head { display: flex; justify-content: space-between; gap: 15px; align-items: flex-start; }
        .details h2 { margin: 0 0 5px; font-size: 1.25rem; }
        .close { border: 0; border-radius: 7px; padding: 8px 12px; color: #475467; background: #eef2f7; cursor: pointer; }
        .detail-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-top: 22px; }
        .detail-label { color: #667085; font-size: .8rem; }
        .detail-value { margin-top: 5px; font-weight: 650; }
        @media (max-width: 760px) {
          .dashboard { padding: 20px 14px; }
          .summary { grid-template-columns: repeat(2, 1fr); }
          .heading { display: block; }
          .detail-grid { grid-template-columns: repeat(2, 1fr); }
        }
      `}</style>

      <div className="shell">
        <header className="heading">
          <div>
            <h1>Equipment monitoring</h1>
            <p className="subtitle">
              Track operational status and upcoming maintenance across your facility.
            </p>
          </div>
        </header>

        <section className="summary" aria-label="Equipment summary">
          <div className="card"><div className="card-label">Total Equipment</div><div className="card-value">{summary.total}</div></div>
          <div className="card"><div className="card-label">Online</div><div className="card-value online">{summary.online}</div></div>
          <div className="card"><div className="card-label">Offline</div><div className="card-value offline">{summary.offline}</div></div>
          <div className="card"><div className="card-label">Maintenance Due</div><div className="card-value maintenance">{summary.due}</div></div>
        </section>

        <section className="panel controls" aria-label="Equipment filters">
          <div className="control">
            <label htmlFor="equipment-search">Search equipment</label>
            <input
              id="equipment-search"
              type="search"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Search by name, ID, or location"
            />
          </div>
          <div className="control">
            <label htmlFor="status-filter">Filter by status</label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value as EquipmentStatus | "All")
              }
            >
              <option value="All">All statuses</option>
              <option value="Online">Online</option>
              <option value="Offline">Offline</option>
              <option value="Maintenance">Maintenance</option>
            </select>
          </div>
        </section>

        <section className="panel table-wrap" aria-label="Equipment list">
          <table>
            <thead>
              <tr>
                {([
                  ["name", "Equipment"],
                  ["status", "Status"],
                  ["location", "Location"],
                  ["lastMaintenance", "Last maintenance"],
                  ["nextMaintenance", "Next maintenance"],
                ] as [SortKey, string][]).map(([key, label]) => (
                  <th key={key} scope="col">
                    <button type="button" onClick={() => handleSort(key)} aria-label={`Sort by ${label}`}>
                      {label}{sortLabel(key)}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length > 0 ? rows.map((equipment) => (
                <tr
                  key={equipment.id}
                  aria-selected={selectedEquipment?.id === equipment.id}
                  onClick={() => setSelectedEquipment(equipment)}
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedEquipment(equipment);
                    }
                  }}
                >
                  <td><strong>{equipment.name}</strong><br /><small>{equipment.id}</small></td>
                  <td><span className={`status ${equipment.status.toLowerCase()}`}><span className="dot" />{equipment.status}</span></td>
                  <td>{equipment.location}</td>
                  <td>{formatDate(equipment.lastMaintenance)}</td>
                  <td>{formatDate(equipment.nextMaintenance)}</td>
                </tr>
              )) : (
                <tr><td className="empty" colSpan={5}>No equipment matches your search or filter.</td></tr>
              )}
            </tbody>
          </table>
        </section>

        {selectedEquipment && (
          <aside className="panel details" aria-labelledby="details-title">
            <div className="details-head">
              <div>
                <h2 id="details-title">{selectedEquipment.name}</h2>
                <div className="subtitle">{selectedEquipment.id}</div>
              </div>
              <button className="close" type="button" onClick={() => setSelectedEquipment(null)}>Close</button>
            </div>
            <div className="detail-grid">
              <div><div className="detail-label">Status</div><div className={`detail-value status ${selectedEquipment.status.toLowerCase()}`}><span className="dot" />{selectedEquipment.status}</div></div>
              <div><div className="detail-label">Location</div><div className="detail-value">{selectedEquipment.location}</div></div>
              <div><div className="detail-label">Last maintenance</div><div className="detail-value">{formatDate(selectedEquipment.lastMaintenance)}</div></div>
              <div><div className="detail-label">Next maintenance</div><div className="detail-value">{formatDate(selectedEquipment.nextMaintenance)}</div></div>
            </div>
          </aside>
        )}
      </div>
    </main>
  );
}

export default EquipmentDashboard;
