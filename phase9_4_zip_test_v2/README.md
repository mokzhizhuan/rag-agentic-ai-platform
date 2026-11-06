# Equipment Inventory Dashboard

A responsive equipment inventory dashboard built with React, TypeScript, and Vite. The application runs entirely in the browser and uses `localStorage` to persist equipment changes between sessions.

## Features

- View equipment in a responsive inventory table
- Search across:
  - Equipment name
  - Category
  - Serial number
  - Location
  - Assigned user
  - Notes
- Filter equipment by status
- Sort by:
  - Name
  - Category
  - Status
  - Location
  - Purchase date
  - Assigned user
- Summary cards for total, available, in-use, maintenance, and retired equipment
- Add new equipment records
- Edit existing equipment records
- Delete equipment with confirmation
- Browser `localStorage` persistence
- Accessible form labels, buttons, table controls, focus states, and dialog behavior
- Responsive layout for desktop, tablet, and mobile screens
- No backend, API, environment variables, or paid services required

## Prerequisites

Install the following software before starting:

- Node.js 18 or newer
- npm 9 or newer

You can check your installed versions with:

```bash
node --version
npm --version
```

## Installation

From the project directory, install the dependencies:

```bash
npm install
```

## Development

Start the Vite development server:

```bash
npm run dev
```

The application uses Vite's default development port:

```text
http://localhost:5173
```

Open the displayed local URL in a browser.

## Production Build

Create an optimized production build:

```bash
npm run build
```

The generated files are written to the `dist` directory.

The build command runs TypeScript project checking followed by the Vite production build. Run this command yourself after installation to verify the project in your environment.

## Preview the Production Build

After creating a production build, preview it locally with:

```bash
npm run preview
```

Vite will display the local preview URL in the terminal.

## Security Audit

Run the npm dependency audit with:

```bash
npm audit
```

Run this command yourself to review the current dependency security status. Audit results can change over time as advisories and package metadata are updated.

Review any reported advisory before choosing a remediation. Do not use `npm audit fix --force` as a default remediation because it may introduce breaking dependency changes.

## Local Storage Behavior

Equipment data is stored in the browser under the following key:

```text
equipment-inventory-items
```

Changes made through the dashboard are saved automatically when equipment is added, edited, or deleted. The data remains available after refreshing the page in the same browser profile.

If no saved data exists, the application loads the built-in mock equipment dataset. If stored data is invalid or browser storage is unavailable, the application safely falls back to the mock dataset.

Local storage is browser-specific. Clearing site data, using a different browser profile, or opening the application in a different browser will not share the same equipment records.

## Using the Dashboard

### Add Equipment

1. Select **Add equipment**.
2. Complete the equipment form.
3. Select a status and enter the relevant asset details.
4. Select **Save equipment**.

### Edit Equipment

1. Locate an equipment record in the table.
2. Select its **Edit** action.
3. Update the required fields.
4. Select **Save changes**.

### Delete Equipment

1. Select the **Delete** action for an equipment record.
2. Review the confirmation dialog.
3. Select **Delete equipment** to permanently remove the record from local storage.

### Search and Filter

Use the search field to find matching records. Search is case-insensitive and checks equipment names, categories, serial numbers, locations, assigned users, and notes.

Use the status filter to display only equipment with a selected status.

### Sort Records

Select a sortable table heading to sort the records. Selecting the same heading again reverses the sort direction.

## Project Structure

```text
equipment-inventory-dashboard/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── README.md
└── src/
    ├── App.tsx
    ├── main.tsx
    ├── vite-env.d.ts
    ├── styles.css
    ├── components/
    │   ├── DeleteConfirmation.tsx
    │   ├── EquipmentForm.tsx
    │   ├── EquipmentTable.tsx
    │   └── SummaryCards.tsx
    ├── data/
    │   └── mockEquipment.ts
    ├── types/
    │   └── equipment.ts
    └── utils/
        └── equipmentStorage.ts
```

## Technology

- React 18
- TypeScript 5
- Vite 6
- HTML and CSS
- Browser `localStorage`

The project uses only standard React, TypeScript, and Vite dependencies and does not require a backend or external runtime service.
