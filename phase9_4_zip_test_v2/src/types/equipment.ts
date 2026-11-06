export const EQUIPMENT_STATUSES = [
  "Available",
  "In Use",
  "Maintenance",
  "Retired",
] as const;

export type EquipmentStatus = (typeof EQUIPMENT_STATUSES)[number];

export interface Equipment {
  id: string;
  name: string;
  category: string;
  serialNumber: string;
  location: string;
  status: EquipmentStatus;
  assignedTo: string;
  purchaseDate: string;
  notes: string;
}

export type EquipmentFormData = Omit<Equipment, "id">;

export type EquipmentSortKey =
  | "name"
  | "category"
  | "status"
  | "location"
  | "purchaseDate"
  | "assignedTo";

export type SortDirection = "asc" | "desc";

export interface SortConfig {
  key: EquipmentSortKey;
  direction: SortDirection;
}
