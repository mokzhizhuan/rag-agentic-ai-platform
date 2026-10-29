import React, { useMemo, useState } from "react";

type CameraStatus = "online" | "offline";

type Camera = {
  id: number;
  name: string;
  location: string;
  status: CameraStatus;
  lastSeen: string;
  streamUrl: string;
};

type StatusFilter = "all" | CameraStatus;

const initialCameras: Camera[] = [
  {
    id: 1,
    name: "Main Entrance",
    location: "Building A · North Gate",
    status: "online",
    lastSeen: "Live now",
    streamUrl: "https://example.com/stream/1",
  },
  {
    id: 2,
    name: "Parking Lot",
    location: "Building A · East Lot",
    status: "online",
    lastSeen: "Live now",
    streamUrl: "https://example.com/stream/2",
  },
  {
    id: 3,
    name: "Warehouse Loading Bay",
    location: "Building B · Dock 2",
    status: "offline",
    lastSeen: "12 minutes ago",
    streamUrl: "https://example.com/stream/3",
  },
  {
    id: 4,
    name: "Reception Desk",
    location: "Building A · Ground Floor",
    status: "online",
    lastSeen: "Live now",
    streamUrl: "https://example.com/stream/4",
  },
  {
    id: 5,
    name: "South Stairwell",
    location: "Building B · Level 1",
    status: "offline",
    lastSeen: "1 hour ago",
    streamUrl: "https://example.com/stream/5",
  },
  {
    id: 6,
    name: "Server Room",
    location: "Building C · Secure Area",
    status: "online",
    lastSeen: "Live now",
    streamUrl: "https://example.com/stream/6",
  },
];

const statusLabels: Record<StatusFilter, string> = {
  all: "All cameras",
  online: "Online",
  offline: "Offline",
};

export default function CctvDashboard(): React.JSX.Element {
  const [cameras] = useState<Camera[]>(initialCameras);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [message, setMessage] = useState("");

  const counts = useMemo(
    () => ({
      all: cameras.length,
      online: cameras.filter((camera) => camera.status === "online").length,
      offline: cameras.filter((camera) => camera.status === "offline").length,
    }),
    [cameras]
  );

  const filteredCameras = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return cameras.filter((camera) => {
      const matchesStatus = status === "all" || camera.status === status;
      const matchesQuery =
        !normalizedQuery ||
        `${camera.name} ${camera.location}`.toLowerCase().includes(normalizedQuery);

      return matchesStatus && matchesQuery;
    });
  }, [cameras, query, status]);

  const handleCameraAction = (camera: Camera, action: "view" | "details") => {
    setMessage(
      action === "view"
        ? `Opening live view for ${camera.name}.`
        : `Showing details for ${camera.name}.`
    );
  };

  return (
    <main className="dashboard">
      <style>{`
        * { box-sizing: border-box; }
        body { margin: 0; background: #f4f7fb; color: #172033; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        button, input { font: inherit; }
        .dashboard { min-height: 100vh; padding: 32px; }
        .shell { max-width: 1240px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 28px; }
        .eyebrow { color: #4169e1; font-size: 12px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; margin: 0 0 8px; }
        h1 { font-size: clamp(28px, 4vw, 40px); line-height: 1.1; margin: 0 0 8px; }
        .subtitle { color: #667085; margin: 0; }
        .live-badge { display: flex; align-items: center; gap: 8px; color: #18794e; background: #e8f7ef; border-radius: 999px; padding: 9px 14px; font-size: 13px; font-weight: 700; white-space: nowrap; }
        .dot { width: 9px; height: 9px; background: currentColor; border-radius: 50%; }
        .summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 26px; }
        .summary-card, .camera-card, .filters { background: white; border: 1px solid #e4e9f1; border-radius: 16px; box-shadow: 0 5px 18px rgba(28, 45, 74, .05); }
        .summary-card { padding: 20px; }
        .summary-label { color: #667085; font-size: 14px; }
        .summary-value { display: block; font-size: 30px; font-weight: 800; margin-top: 9px; }
        .filters { display: flex; align-items: center; gap: 16px; padding: 16px; margin-bottom: 24px; }
        .search { flex: 1; min-width: 180px; border: 1px solid #d8dfeb; border-radius: 10px; padding: 11px 13px; color: #172033; outline: none; }
        .search:focus, .filter-button:focus-visible, .action:focus-visible { outline: 3px solid #b8c9ff; outline-offset: 2px; }
        .filter-group { display: flex; gap: 7px; flex-wrap: wrap; }
        .filter-button, .action { border: 0; border-radius: 9px; cursor: pointer; }
        .filter-button { background: #f0f3f8; color: #536174; padding: 10px 13px; font-weight: 700; }
        .filter-button[aria-pressed="true"] { background: #4169e1; color: white; }
        .camera-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
        .camera-card { overflow: hidden; }
        .preview { height: 145px; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #182642, #344d78); color: #dce6ff; font-size: 14px; font-weight: 700; letter-spacing: .04em; }
        .preview.offline { background: linear-gradient(135deg, #424b5b, #697386); color: #eef1f6; }
        .camera-content { padding: 17px; }
        .camera-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
        .camera-name { font-size: 17px; font-weight: 800; margin: 0 0 5px; }
        .location, .last-seen { color: #667085; font-size: 13px; margin: 0; }
        .status { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 5px 8px; font-size: 11px; font-weight: 800; text-transform: uppercase; }
        .status.online { background: #e8f7ef; color: #18794e; }
        .status.offline { background: #fff0f0; color: #b42318; }
        .camera-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 18px; }
        .actions { display: flex; gap: 7px; }
        .action { background: #edf2ff; color: #3156c5; padding: 8px 10px; font-size: 12px; font-weight: 800; }
        .action.secondary { background: #f2f4f7; color: #536174; }
        .empty { padding: 52px 20px; text-align: center; background: white; border: 1px dashed #cbd5e1; border-radius: 16px; color: #667085; }
        .announcement { min-height: 20px; color: #3156c5; font-size: 13px; margin: 10px 0; }
        @media (max-width: 850px) { .camera-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 620px) { .dashboard { padding: 20px 14px; } .header, .filters { align-items: stretch; flex-direction: column; } .summary { gap: 10px; } .summary-card { padding: 15px; } .summary-value { font-size: 25px; } .camera-grid { grid-template-columns: 1fr; } .live-badge { align-self: flex-start; } }
      `}</style>

      <div className="shell">
        <header className="header">
          <div>
            <p className="eyebrow">Security operations</p>
            <h1>CCTV monitoring</h1>
            <p className="subtitle">Monitor and manage your connected camera network.</p>
          </div>
          <div className="live-badge" aria-label="System status: operational">
            <span className="dot" aria-hidden="true" />
            System operational
          </div>
        </header>

        <section className="summary" aria-label="Camera summary">
          <div className="summary-card">
            <span className="summary-label">Total cameras</span>
            <strong className="summary-value">{counts.all}</strong>
          </div>
          <div className="summary-card">
            <span className="summary-label">Online</span>
            <strong className="summary-value" style={{ color: "#18794e" }}>{counts.online}</strong>
          </div>
          <div className="summary-card">
            <span className="summary-label">Offline</span>
            <strong className="summary-value" style={{ color: "#b42318" }}>{counts.offline}</strong>
          </div>
        </section>

        <section className="filters" aria-label="Camera filters">
          <label htmlFor="camera-search" style={{ display: "none" }}>Search cameras</label>
          <input
            id="camera-search"
            className="search"
            type="search"
            placeholder="Search by camera or location..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="filter-group" role="group" aria-label="Filter by status">
            {(Object.keys(statusLabels) as StatusFilter[]).map((option) => (
              <button
                key={option}
                className="filter-button"
                type="button"
                aria-pressed={status === option}
                onClick={() => setStatus(option)}
              >
                {statusLabels[option]} ({counts[option]})
              </button>
            ))}
          </div>
        </section>

        <p className="announcement" role="status" aria-live="polite">{message}</p>

        {filteredCameras.length > 0 ? (
          <section className="camera-grid" aria-label={`${filteredCameras.length} cameras`}>
            {filteredCameras.map((camera) => (
              <article className="camera-card" key={camera.id}>
                <div className={`preview ${camera.status}`} aria-label={`${camera.name} camera preview`}>
                  {camera.status === "online" ? "LIVE PREVIEW" : "SIGNAL UNAVAILABLE"}
                </div>
                <div className="camera-content">
                  <div className="camera-top">
                    <div>
                      <h2 className="camera-name">{camera.name}</h2>
                      <p className="location">{camera.location}</p>
                    </div>
                    <span className={`status ${camera.status}`}>
                      <span className="dot" aria-hidden="true" />
                      {camera.status}
                    </span>
                  </div>
                  <div className="camera-footer">
                    <p className="last-seen">{camera.lastSeen}</p>
                    <div className="actions">
                      <button className="action" type="button" onClick={() => handleCameraAction(camera, "view")}>
                        View
                      </button>
                      <button className="action secondary" type="button" onClick={() => handleCameraAction(camera, "details")}>
                        Details
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </section>
        ) : (
          <section className="empty" aria-live="polite">
            <strong>No cameras found</strong>
            <p>Try changing your search or status filter.</p>
          </section>
        )}
      </div>
    </main>
  );
}
