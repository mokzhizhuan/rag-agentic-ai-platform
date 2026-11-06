import { useEffect, useRef } from "react";
import type { Equipment } from "../types/equipment";

interface DeleteConfirmationProps {
  equipment: Equipment | null;
  visible: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function DeleteConfirmation({
  equipment,
  visible,
  onConfirm,
  onCancel,
}: DeleteConfirmationProps) {
  const cancelButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!visible) {
      return;
    }

    cancelButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCancel();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [visible, onCancel]);

  useEffect(() => {
    if (!visible) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [visible]);

  if (!visible || !equipment) {
    return null;
  }

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onCancel();
        }
      }}
    >
      <section
        className="modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
      >
        <div className="modal-icon" aria-hidden="true">
          !
        </div>

        <div className="modal-content">
          <h2 id="delete-dialog-title">Delete equipment?</h2>
          <p id="delete-dialog-description">
            Are you sure you want to delete{" "}
            <strong>{equipment.name}</strong>? This action cannot be undone.
          </p>

          <dl className="confirmation-details">
            <div>
              <dt>Serial number</dt>
              <dd>{equipment.serialNumber}</dd>
            </div>
            <div>
              <dt>Location</dt>
              <dd>{equipment.location}</dd>
            </div>
          </dl>
        </div>

        <div className="modal-actions">
          <button
            ref={cancelButtonRef}
            type="button"
            className="button button-secondary"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="button button-danger"
            onClick={onConfirm}
          >
            Delete equipment
          </button>
        </div>
      </section>
    </div>
  );
}
