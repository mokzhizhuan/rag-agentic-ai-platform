import { FormEvent, useEffect, useState } from "react";
import {
  EQUIPMENT_STATUSES,
  Equipment,
  EquipmentFormData,
  EquipmentStatus,
} from "../types/equipment";

interface EquipmentFormProps {
  equipment?: Equipment | null;
  onSubmit: (data: EquipmentFormData) => void;
  onCancel: () => void;
}

type FormErrors = Partial<Record<keyof EquipmentFormData, string>>;

const emptyForm: EquipmentFormData = {
  name: "",
  category: "",
  serialNumber: "",
  location: "",
  status: "Available",
  assignedTo: "",
  purchaseDate: "",
  notes: "",
};

function getFormData(equipment?: Equipment | null): EquipmentFormData {
  if (!equipment) {
    return emptyForm;
  }

  return {
    name: equipment.name,
    category: equipment.category,
    serialNumber: equipment.serialNumber,
    location: equipment.location,
    status: equipment.status,
    assignedTo: equipment.assignedTo,
    purchaseDate: equipment.purchaseDate,
    notes: equipment.notes,
  };
}

export default function EquipmentForm({
  equipment,
  onSubmit,
  onCancel,
}: EquipmentFormProps) {
  const [formData, setFormData] = useState<EquipmentFormData>(() =>
    getFormData(equipment),
  );
  const [errors, setErrors] = useState<FormErrors>({});

  const isEditing = Boolean(equipment);

  useEffect(() => {
    setFormData(getFormData(equipment));
    setErrors({});
  }, [equipment]);

  function updateField<K extends keyof EquipmentFormData>(
    field: K,
    value: EquipmentFormData[K],
  ) {
    setFormData((current) => ({
      ...current,
      [field]: value,
    }));

    if (errors[field]) {
      setErrors((current) => ({
        ...current,
        [field]: undefined,
      }));
    }
  }

  function validate(): FormErrors {
    const nextErrors: FormErrors = {};

    if (!formData.name.trim()) {
      nextErrors.name = "Enter an equipment name.";
    }

    if (!formData.category.trim()) {
      nextErrors.category = "Enter a category.";
    }

    if (!formData.serialNumber.trim()) {
      nextErrors.serialNumber = "Enter a serial number.";
    }

    if (!formData.location.trim()) {
      nextErrors.location = "Enter a location.";
    }

    if (!formData.purchaseDate) {
      nextErrors.purchaseDate = "Select a purchase date.";
    }

    return nextErrors;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    onSubmit({
      name: formData.name.trim(),
      category: formData.category.trim(),
      serialNumber: formData.serialNumber.trim(),
      location: formData.location.trim(),
      status: formData.status,
      assignedTo: formData.assignedTo.trim(),
      purchaseDate: formData.purchaseDate,
      notes: formData.notes.trim(),
    });
  }

  return (
    <section className="form-panel" aria-labelledby="equipment-form-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isEditing ? "Update record" : "New record"}</p>
          <h2 id="equipment-form-title">
            {isEditing ? "Edit equipment" : "Add equipment"}
          </h2>
        </div>
      </div>

      <form className="equipment-form" onSubmit={handleSubmit} noValidate>
        <div className="form-grid">
          <div className="form-field">
            <label htmlFor="equipment-name">
              Equipment name <span aria-hidden="true">*</span>
            </label>
            <input
              id="equipment-name"
              name="name"
              type="text"
              value={formData.name}
              onChange={(event) => updateField("name", event.target.value)}
              aria-invalid={Boolean(errors.name)}
              aria-describedby={errors.name ? "equipment-name-error" : undefined}
              autoComplete="off"
              required
            />
            {errors.name && (
              <p className="field-error" id="equipment-name-error">
                {errors.name}
              </p>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="equipment-category">
              Category <span aria-hidden="true">*</span>
            </label>
            <input
              id="equipment-category"
              name="category"
              type="text"
              value={formData.category}
              onChange={(event) => updateField("category", event.target.value)}
              aria-invalid={Boolean(errors.category)}
              aria-describedby={
                errors.category ? "equipment-category-error" : undefined
              }
              placeholder="e.g. Laptop, Monitor"
              required
            />
            {errors.category && (
              <p className="field-error" id="equipment-category-error">
                {errors.category}
              </p>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="equipment-serial-number">
              Serial number <span aria-hidden="true">*</span>
            </label>
            <input
              id="equipment-serial-number"
              name="serialNumber"
              type="text"
              value={formData.serialNumber}
              onChange={(event) =>
                updateField("serialNumber", event.target.value)
              }
              aria-invalid={Boolean(errors.serialNumber)}
              aria-describedby={
                errors.serialNumber ? "equipment-serial-error" : undefined
              }
              autoComplete="off"
              required
            />
            {errors.serialNumber && (
              <p className="field-error" id="equipment-serial-error">
                {errors.serialNumber}
              </p>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="equipment-location">
              Location <span aria-hidden="true">*</span>
            </label>
            <input
              id="equipment-location"
              name="location"
              type="text"
              value={formData.location}
              onChange={(event) => updateField("location", event.target.value)}
              aria-invalid={Boolean(errors.location)}
              aria-describedby={
                errors.location ? "equipment-location-error" : undefined
              }
              placeholder="e.g. New York Office"
              required
            />
            {errors.location && (
              <p className="field-error" id="equipment-location-error">
                {errors.location}
              </p>
            )}
          </div>

          <div className="form-field">
            <label htmlFor="equipment-status">Status</label>
            <select
              id="equipment-status"
              name="status"
              value={formData.status}
              onChange={(event) =>
                updateField("status", event.target.value as EquipmentStatus)
              }
            >
              {EQUIPMENT_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="equipment-assigned-to">Assigned to</label>
            <input
              id="equipment-assigned-to"
              name="assignedTo"
              type="text"
              value={formData.assignedTo}
              onChange={(event) =>
                updateField("assignedTo", event.target.value)
              }
              placeholder="e.g. Jordan Lee"
            />
          </div>

          <div className="form-field">
            <label htmlFor="equipment-purchase-date">
              Purchase date <span aria-hidden="true">*</span>
            </label>
            <input
              id="equipment-purchase-date"
              name="purchaseDate"
              type="date"
              value={formData.purchaseDate}
              onChange={(event) =>
                updateField("purchaseDate", event.target.value)
              }
              aria-invalid={Boolean(errors.purchaseDate)}
              aria-describedby={
                errors.purchaseDate ? "equipment-date-error" : undefined
              }
              required
            />
            {errors.purchaseDate && (
              <p className="field-error" id="equipment-date-error">
                {errors.purchaseDate}
              </p>
            )}
          </div>

          <div className="form-field form-field-wide">
            <label htmlFor="equipment-notes">Notes</label>
            <textarea
              id="equipment-notes"
              name="notes"
              value={formData.notes}
              onChange={(event) => updateField("notes", event.target.value)}
              rows={4}
              placeholder="Add useful details about this equipment"
            />
          </div>
        </div>

        <div className="form-actions">
          <button className="button button-secondary" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button className="button button-primary" type="submit">
            {isEditing ? "Save changes" : "Add equipment"}
          </button>
        </div>
      </form>
    </section>
  );
}
