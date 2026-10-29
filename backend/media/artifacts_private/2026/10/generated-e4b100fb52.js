/**
 * CCTV device record management utilities.
 *
 * @module cctv-devices
 */

/**
 * Canonical device statuses.
 * @type {Readonly<{
 *   ONLINE: string,
 *   OFFLINE: string,
 *   MAINTENANCE: string,
 *   UNKNOWN: string
 * }>}
 */
export const DEVICE_STATUSES = Object.freeze({
  ONLINE: "online",
  OFFLINE: "offline",
  MAINTENANCE: "maintenance",
  UNKNOWN: "unknown"
});

/**
 * Canonical device severity levels.
 * @type {Readonly<{
 *   LOW: string,
 *   MEDIUM: string,
 *   HIGH: string,
 *   CRITICAL: string
 * }>}
 */
export const DEVICE_SEVERITIES = Object.freeze({
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical"
});

const STATUS_VALUES = Object.freeze(Object.values(DEVICE_STATUSES));
const SEVERITY_VALUES = Object.freeze(Object.values(DEVICE_SEVERITIES));

const STATUS_ALIASES = Object.freeze({
  active: DEVICE_STATUSES.ONLINE,
  connected: DEVICE_STATUSES.ONLINE,
  up: DEVICE_STATUSES.ONLINE,
  online: DEVICE_STATUSES.ONLINE,
  inactive: DEVICE_STATUSES.OFFLINE,
  disconnected: DEVICE_STATUSES.OFFLINE,
  down: DEVICE_STATUSES.OFFLINE,
  offline: DEVICE_STATUSES.OFFLINE,
  servicing: DEVICE_STATUSES.MAINTENANCE,
  maintenance: DEVICE_STATUSES.MAINTENANCE,
  unknown: DEVICE_STATUSES.UNKNOWN,
  unavailable: DEVICE_STATUSES.UNKNOWN
});

/**
 * @typedef {Object} Device
 * @property {string} identifier Unique device identifier.
 * @property {string} name Human-readable device name.
 * @property {"online"|"offline"|"maintenance"|"unknown"} status
 * @property {"low"|"medium"|"high"|"critical"} severity
 * @property {string} location Physical or logical device location.
 * @property {Record<string, unknown>} [metadata] Optional additional fields.
 */

/**
 * Normalize a status value to a canonical status string.
 *
 * @param {unknown} status Status to normalize.
 * @returns {"online"|"offline"|"maintenance"|"unknown"}
 * @throws {TypeError} If status is not a string.
 * @throws {RangeError} If status is not recognized.
 */
export function normalizeStatus(status) {
  if (typeof status !== "string") {
    throw new TypeError("Status must be a string.");
  }

  const normalized = status.trim().toLowerCase();
  const canonical = STATUS_ALIASES[normalized];

  if (!canonical) {
    throw new RangeError(
      `Unsupported status "${status}". Allowed values: ${STATUS_VALUES.join(", ")}.`
    );
  }

  return canonical;
}

/**
 * Validate a CCTV device record.
 *
 * @param {unknown} device Device record to validate.
 * @returns {true} True when the device is valid.
 * @throws {TypeError} If the record or a required field has an invalid type.
 * @throws {RangeError} If a value is empty or outside the allowed values.
 */
export function validateDevice(device) {
  if (device === null || typeof device !== "object" || Array.isArray(device)) {
    throw new TypeError("Device must be a non-null object.");
  }

  const requiredStrings = ["identifier", "name", "location"];

  for (const field of requiredStrings) {
    if (!(field in device)) {
      throw new TypeError(`Device.${field} is required.`);
    }
    if (typeof device[field] !== "string") {
      throw new TypeError(`Device.${field} must be a string.`);
    }
    if (device[field].trim() === "") {
      throw new RangeError(`Device.${field} must not be empty.`);
    }
  }

  if (!("status" in device)) {
    throw new TypeError("Device.status is required.");
  }
  normalizeStatus(device.status);

  if (!("severity" in device)) {
    throw new TypeError("Device.severity is required.");
  }
  if (typeof device.severity !== "string") {
    throw new TypeError("Device.severity must be a string.");
  }

  const severity = device.severity.trim().toLowerCase();
  if (!SEVERITY_VALUES.includes(severity)) {
    throw new RangeError(
      `Unsupported severity "${device.severity}". Allowed values: ${SEVERITY_VALUES.join(", ")}.`
    );
  }

  if ("metadata" in device &&
      (device.metadata === null ||
       typeof device.metadata !== "object" ||
       Array.isArray(device.metadata))) {
    throw new TypeError("Device.metadata must be a non-null object when provided.");
  }

  return true;
}

/**
 * Filter devices by optional status and severity criteria.
 *
 * @param {unknown} devices Array of device records.
 * @param {{status?: string|string[], severity?: string|string[]}} [criteria]
 * @returns {Device[]} A new array containing matching devices.
 * @throws {TypeError} If devices, criteria, or criteria values are malformed.
 * @throws {RangeError} If a criterion contains an unsupported value.
 */
export function filterDevices(devices, criteria = {}) {
  if (!Array.isArray(devices)) {
    throw new TypeError("devices must be an array.");
  }
  if (criteria === null || typeof criteria !== "object" || Array.isArray(criteria)) {
    throw new TypeError("criteria must be an object.");
  }

  const normalizeCriterion = (value, normalizer, label) => {
    if (value === undefined) return undefined;
    const values = Array.isArray(value) ? value : [value];
    if (values.length === 0) return [];
    return values.map((entry) => {
      if (typeof entry !== "string") {
        throw new TypeError(`${label} criteria values must be strings.`);
      }
      return normalizer(entry);
    });
  };

  const statuses = normalizeCriterion(criteria.status, normalizeStatus, "status");
  const severities = normalizeCriterion(
    criteria.severity,
    (value) => {
      const normalized = value.trim().toLowerCase();
      if (!SEVERITY_VALUES.includes(normalized)) {
        throw new RangeError(`Unsupported severity "${value}".`);
      }
      return normalized;
    },
    "severity"
  );

  return devices.filter((device) => {
    validateDevice(device);
    const status = normalizeStatus(device.status);
    const severity = device.severity.trim().toLowerCase();
    const statusMatches = statuses === undefined || statuses.includes(status);
    const severityMatches =
      severities === undefined || severities.includes(severity);
    return statusMatches && severityMatches;
  });
}

/**
 * Calculate totals and grouped statistics for devices.
 *
 * @param {unknown} devices Array of device records.
 * @returns {{
 *   total: number,
 *   byStatus: Record<string, number>,
 *   bySeverity: Record<string, number>,
 *   byLocation: Record<string, number>
 * }}
 * @throws {TypeError} If devices is not an array or contains malformed records.
 * @throws {RangeError} If a record contains an invalid value.
 */
export function calculateSummary(devices) {
  if (!Array.isArray(devices)) {
    throw new TypeError("devices must be an array.");
  }

  const byStatus = Object.fromEntries(STATUS_VALUES.map((status) => [status, 0]));
  const bySeverity = Object.fromEntries(SEVERITY_VALUES.map((severity) => [severity, 0]));
  const byLocation = {};

  for (const device of devices) {
    validateDevice(device);
    const status = normalizeStatus(device.status);
    const severity = device.severity.trim().toLowerCase();

    byStatus[status] += 1;
    bySeverity[severity] += 1;
    byLocation[device.location] = (byLocation[device.location] || 0) + 1;
  }

  return {
    total: devices.length,
    byStatus,
    bySeverity,
    byLocation
  };
}

/**
 * Export device records as CSV.
 *
 * @param {unknown} devices Array of device records.
 * @returns {string} CSV text including a header row.
 * @throws {TypeError} If devices is not an array or contains malformed records.
 * @throws {RangeError} If a record contains an invalid value.
 */
export function exportDevicesToCSV(devices) {
  if (!Array.isArray(devices)) {
    throw new TypeError("devices must be an array.");
  }

  const headers = ["identifier", "name", "status", "severity", "location", "metadata"];
  const escapeCSV = (value) => {
    const text = value === undefined || value === null ? "" : String(value);
    return /[",\r\n]/.test(text)
      ? `"${text.replace(/"/g, "\"\"")}"`
      : text;
  };

  const rows = [headers.map(escapeCSV).join(",")];

  for (const device of devices) {
    validateDevice(device);
    rows.push([
      device.identifier,
      device.name,
      normalizeStatus(device.status),
      device.severity.trim().toLowerCase(),
      device.location,
      device.metadata === undefined ? "" : JSON.stringify(device.metadata)
    ].map(escapeCSV).join(","));
  }

  return rows.join("\r\n");
}
