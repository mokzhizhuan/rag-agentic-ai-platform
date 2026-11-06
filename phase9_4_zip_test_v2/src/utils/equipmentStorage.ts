import { mockEquipment } from "../data/mockEquipment";
import {
  EQUIPMENT_STATUSES,
  type Equipment,
  type EquipmentStatus,
} from "../types/equipment";

export const EQUIPMENT_STORAGE_KEY = "equipment-inventory-items";

const isEquipmentStatus = (value: unknown): value is EquipmentStatus =>
  typeof value === "string" &&
  (EQUIPMENT_STATUSES as readonly string[]).includes(value);

const isEquipment = (value: unknown): value is Equipment => {
  if (!value || typeof value !== "object") {
    return false;
  }

  const equipment = value as Partial<Equipment>;

  return (
    typeof equipment.id === "string" &&
    typeof equipment.name === "string" &&
    typeof equipment.category === "string" &&
    typeof equipment.serialNumber === "string" &&
    typeof equipment.location === "string" &&
    isEquipmentStatus(equipment.status) &&
    typeof equipment.assignedTo === "string" &&
    typeof equipment.purchaseDate === "string" &&
    typeof equipment.notes === "string"
  );
};

const cloneMockEquipment = (): Equipment[] =>
  mockEquipment.map((equipment) => ({ ...equipment }));

export const loadEquipment = (): Equipment[] => {
  if (typeof window === "undefined" || !window.localStorage) {
    return cloneMockEquipment();
  }

  try {
    const storedValue = window.localStorage.getItem(EQUIPMENT_STORAGE_KEY);

    if (!storedValue) {
      return cloneMockEquipment();
    }

    const parsedValue: unknown = JSON.parse(storedValue);

    if (!Array.isArray(parsedValue) || !parsedValue.every(isEquipment)) {
      return cloneMockEquipment();
    }

    return parsedValue.map((equipment) => ({ ...equipment }));
  } catch {
    return cloneMockEquipment();
  }
};

export const saveEquipment = (equipment: Equipment[]): boolean => {
  if (typeof window === "undefined" || !window.localStorage) {
    return false;
  }

  try {
    window.localStorage.setItem(
      EQUIPMENT_STORAGE_KEY,
      JSON.stringify(equipment),
    );
    return true;
  } catch {
    return false;
  }
};
