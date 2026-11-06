import { useEffect, useState } from "react";
import EquipmentForm from "./components/EquipmentForm";
import EquipmentTable from "./components/EquipmentTable";
import DeleteConfirmation from "./components/DeleteConfirmation";
import SummaryCards from "./components/SummaryCards";
import { loadEquipment, saveEquipment } from "./utils/equipmentStorage";
import type {
  Equipment,
  EquipmentFormData,
  EquipmentSortKey,
  SortConfig,
  EquipmentStatus,
} from "./types/equipment";

type StatusFilter = EquipmentStatus | "All";

function createEquipmentId(): string {
  return `eq-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function App(): JSX.Element {
  const [equipment, setEquipment] = useState<Equipment[]>(() => loadEquipment());
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All");
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: "name",
    direction: "asc",
  });
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [editingEquipment, setEditingEquipment] = useState<Equipment | null>(
    null,
  );
  const [equipmentToDelete, setEquipmentToDelete] =
    useState<Equipment | null>(null);

  useEffect(() => {
    saveEquipment(equipment);
  }, [equipment]);

  function openAddForm(): void {
    setEditingEquipment(null);
    setIsFormVisible(true);
    window.requestAnimationFrame(() => {
      document
        .getElementById("equipment-name")
        ?.focus();
    });
  }

  function openEditForm(item: Equipment): void {
    setEditingEquipment(item);
    setIsFormVisible(true);
    window.requestAnimationFrame(() => {
      document
        .getElementById("equipment-name")
        ?.focus();
    });
  }

  function closeForm(): void {
    setIsFormVisible(false);
    setEditingEquipment(null);
  }

  function handleSubmit(formData: EquipmentFormData): void {
    if (editingEquipment) {
      setEquipment((current) =>
        current.map((item) =>
          item.id === editingEquipment.id
            ? { ...formData, id: editingEquipment.id }
            : item,
        ),
      );
    } else {
      setEquipment((current) => [
        ...current,
        {
          ...formData,
          id: createEquipmentId(),
        },
      ]);
    }

    closeForm();
  }

  function confirmDelete(): void {
    if (!equipmentToDelete) {
      return;
    }

    setEquipment((current) =>
      current.filter((item) => item.id !== equipmentToDelete.id),
    );
    setEquipmentToDelete(null);
  }

  function handleSort(key: EquipmentSortKey): void {
    setSortConfig((current) => ({
      key,
      direction:
        current.key === key && current.direction === "asc" ? "desc" : "asc",
    }));
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__inner">
          <div className="brand">
            <div className="brand__mark" aria-hidden="true">
              EI
            </div>
            <div>
              <p className="eyebrow">Operations workspace</p>
              <h1>Equipment inventory</h1>
            </div>
          </div>

          <button className="button button--primary" type="button" onClick={openAddForm}>
            <span aria-hidden="true">+</span>
            Add equipment
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="page-intro" aria-labelledby="page-title">
          <div>
            <p className="eyebrow">Asset management</p>
            <h2 id="page-title">Keep every asset accounted for.</h2>
            <p className="page-intro__description">
              Track equipment status, ownership, location, and lifecycle
              details from one organized workspace.
            </p>
          </div>
        </section>

        <SummaryCards equipment={equipment} />

        {isFormVisible && (
          <EquipmentForm
            equipment={editingEquipment}
            onSubmit={handleSubmit}
            onCancel={closeForm}
          />
        )}

        <EquipmentTable
          equipment={equipment}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          sortConfig={sortConfig}
          onSort={handleSort}
          onEdit={openEditForm}
          onDelete={setEquipmentToDelete}
        />
      </main>

      <DeleteConfirmation
        equipment={equipmentToDelete}
        visible={Boolean(equipmentToDelete)}
        onConfirm={confirmDelete}
        onCancel={() => setEquipmentToDelete(null)}
      />
    </div>
  );
}
