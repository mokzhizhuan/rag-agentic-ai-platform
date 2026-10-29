/**
 * @typedef {Object} DeviceRecord
 * @property {string|number} id
 * @property {string} name
 * @property {string} status
 * @property {number} severity
 * @property {string} [location]
 * @property {string} [ipAddress]
 * @property {string} [lastSeen]
 * @property {Record<string, unknown>} [extra]
 */

/**
 * @typedef {Object} ValidationError
 * @property {string} field
 * @property {string} code
 * @property {string} message
 */

/**
 * @typedef {Object} ValidationResult
 * @property {boolean} valid
 * @property {ValidationError[]} errors
 * @property {DeviceRecord} [device]
 */

/**
 * @typedef {Object} FilterOptions
 * @property {string|string[]} [status]
 * @property {string|string[]} [statuses]
 * @property {number|number[]} [severity]
 * @property {number|number[]} [severities]
 * @property {number} [minSeverity]
 * @property {number} [maxSeverity]
 */

/**
 * @typedef {Object} SummaryStatistics
 * @property {number} total
 * @property {number} valid
 * @property {number} invalid
 * @property {Record<string, number>} severityTotals
 * @property {Record<string, number>} statusTotals
 */

/**
 * @typedef {Object} CsvOptions
 * @property {string[]} [columns]
 * @property {string} [delimiter]
 * @property {boolean} [includeHeader]
 */

/**
 * Normalize a camera status to a canonical value.
 *
 * @param {string} status
 * @returns {string}
 */
export function normalizeStatus(status) {
  if (typeof status !== "string") {
    throw new TypeError("status must be a string.");
  }

  const value = status.trim().toLowerCase();
  const aliases = {
    online: "online",
    active: "online",
    up: "online",
    connected: "online",
    offline: "offline",
    inactive: "offline",
    down: "offline",
    disconnected: "offline",
    maintenance: "maintenance",
    servicing: "maintenance",
    service: "maintenance",
    repair: "maintenance",
    unknown: "unknown",
    unavailable: "unknown"
  };

  return aliases[value] || "unknown";
}

/**
 * Validate a device record and return structured validation errors.
 *
 * @param {unknown} device
 * @returns {ValidationResult}
 */
export function validateDevice(device) {
  const errors = [];

  if (device === null || typeof device !== "object" || Array.isArray(device)) {
    return {
      valid: false,
      errors: [{
        field: "device",
        code: "invalid_type",
        message: "Device must be a non-null object."
      }]
    };
  }

  if (
    (typeof device.id !== "string" && typeof device.id !== "number") ||
    (typeof device.id === "string" && device.id.trim() === "") ||
    (typeof device.id === "number" && !Number.isFinite(device.id))
  ) {
    errors.push({
      field: "id",
      code: "required_or_invalid",
      message: "id is required and must be a non-empty string or finite number."
    });
  }

  if (typeof device.name !== "string" || device.name.trim() === "") {
    errors.push({
      field: "name",
      code: "required_or_invalid",
      message: "name is required and must be a non-empty string."
    });
  }

  if (typeof device.status !== "string" || device.status.trim() === "") {
    errors.push({
      field: "status",
      code: "required_or_invalid",
      message: "status is required and must be a non-empty string."
    });
  }

  if (
    typeof device.severity !== "number" ||
    !Number.isInteger(device.severity) ||
    device.severity < 1 ||
    device.severity > 5
  ) {
    errors.push({
      field: "severity",
      code: "range_or_type",
      message: "severity is required and must be an integer from 1 through 5."
    });
  }

  return errors.length === 0
    ? { valid: true, errors: [], device }
    : { valid: false, errors };
}

function assertDeviceArray(devices, argumentName = "devices") {
  if (!Array.isArray(devices)) {
    throw new TypeError(`${argumentName} must be an array.`);
  }
}

function toArray(value, fieldName) {
  if (value === undefined) return undefined;
  const values = Array.isArray(value) ? value : [value];
  if (values.length === 0) {
    throw new RangeError(`${fieldName} must not be empty.`);
  }
  return values;
}

/**
 * Filter device records by normalized status and severity.
 *
 * @param {DeviceRecord[]} devices
 * @param {FilterOptions} [options]
 * @returns {DeviceRecord[]}
 */
export function filterDevices(devices, options = {}) {
  assertDeviceArray(devices);

  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new TypeError("options must be an object.");
  }

  const rawStatuses = options.statuses ?? options.status;
  const rawSeverities = options.severities ?? options.severity;
  const statuses = toArray(rawStatuses, "status").map(normalizeStatus);
  const severities = toArray(rawSeverities, "severity");

  for (const severity of severities || []) {
    if (!Number.isInteger(severity) || severity < 1 || severity > 5) {
      throw new RangeError("severity filters must contain integers from 1 through 5.");
    }
  }

  for (const [name, value] of [["minSeverity", options.minSeverity], ["maxSeverity", options.maxSeverity]]) {
    if (value !== undefined && (!Number.isInteger(value) || value < 1 || value > 5)) {
      throw new RangeError(`${name} must be an integer from 1 through 5.`);
    }
  }

  if (
    options.minSeverity !== undefined &&
    options.maxSeverity !== undefined &&
    options.minSeverity > options.maxSeverity
  ) {
    throw new RangeError("minSeverity cannot exceed maxSeverity.");
  }

  return devices.filter((device) => {
    const statusMatches = !statuses || statuses.includes(normalizeStatus(device?.status ?? ""));
    const severity = device?.severity;
    const severityMatches =
      (!severities || severities.includes(severity)) &&
      (options.minSeverity === undefined || severity >= options.minSeverity) &&
      (options.maxSeverity === undefined || severity <= options.maxSeverity);

    return statusMatches && severityMatches;
  });
}

/**
 * Calculate device counts grouped by severity and status.
 *
 * @param {DeviceRecord[]} devices
 * @returns {SummaryStatistics}
 */
export function calculateSummary(devices) {
  assertDeviceArray(devices);

  const summary = {
    total: devices.length,
    valid: 0,
    invalid: 0,
    severityTotals: {},
    statusTotals: {}
  };

  for (const device of devices) {
    const result = validateDevice(device);
    if (!result.valid) {
      summary.invalid += 1;
      continue;
    }

    summary.valid += 1;
    const severityKey = String(device.severity);
    const statusKey = normalizeStatus(device.status);
    summary.severityTotals[severityKey] = (summary.severityTotals[severityKey] || 0) + 1;
    summary.statusTotals[statusKey] = (summary.statusTotals[statusKey] || 0) + 1;
  }

  return summary;
}

function escapeCsv(value, delimiter) {
  const text = value === null || value === undefined ? "" : String(value);
  const escaped = text.replaceAll('"', '""');
  return new RegExp(`[",\\r\\n${delimiter}]`).test(text)
    ? `"${escaped}"`
    : escaped;
}

/**
 * Export device records as CSV.
 *
 * @param {DeviceRecord[]} devices
 * @param {CsvOptions} [options]
 * @returns {string}
 */
export function exportDevicesToCsv(devices, options = {}) {
  assertDeviceArray(devices);

  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new TypeError("options must be an object.");
  }

  const columns = options.columns ?? ["id", "name", "status", "severity"];
  const delimiter = options.delimiter ?? ",";
  const includeHeader = options.includeHeader ?? true;

  if (!Array.isArray(columns) || columns.length === 0 || columns.some((column) => typeof column !== "string" || !column)) {
    throw new TypeError("columns must be a non-empty array of non-empty strings.");
  }
  if (typeof delimiter !== "string" || delimiter.length !== 1 || delimiter === "\r" || delimiter === "\n") {
    throw new TypeError("delimiter must be a single non-newline character.");
  }
  if (typeof includeHeader !== "boolean") {
    throw new TypeError("includeHeader must be a boolean.");
  }

  const rows = [];
  if (includeHeader) {
    rows.push(columns.map((column) => escapeCsv(column, delimiter)).join(delimiter));
  }

  for (const device of devices) {
    rows.push(columns.map((column) => {
      const value = column === "status" && device?.status !== undefined
        ? normalizeStatus(device.status)
        : device?.[column];
      return escapeCsv(value, delimiter);
    }).join(delimiter));
  }

  return rows.join("\r\n");
}
