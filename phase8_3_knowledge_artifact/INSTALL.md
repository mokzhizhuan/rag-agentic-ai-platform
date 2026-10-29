# Phase 8.3 — Knowledge Base & Artifact Studio

Frontend-only visual integration on top of the Phase 8.1/8.2 app. **No changes to API calls, authentication, backend, or generation logic.** This is not the later comprehensive design-polish phase.

## Changes

- Adds `frontend/src/phase8-studios.css` for Knowledge Base and Create Files.
- Adds an import for that stylesheet to `frontend/src/App.tsx`.
- Adds the `knowledge-studio` and `artifact-studio` class names to the two existing page sections, leaving their child content and event handlers unchanged.
- Uses your chosen white workspace background and dark navy content cards.
- Improves artifact attachment text, job progress rows, file cards, ZIP validation reports and preview contrast.

## Install (PowerShell, from project root)

Extract the ZIP into the project directory, then:

```powershell
python .\phase8_3_knowledge_artifact\install.py .
python .\phase8_3_knowledge_artifact\install.py . --apply
docker compose build --pull=false frontend
docker compose up -d --no-build --force-recreate frontend
```

Refresh `http://localhost:5174` with Ctrl+F5.

## Verify

Check Knowledge Base: upload selection, document list, delete, semantic search. Check Create Files: provider/format, prompt, attachments, generation and progress, preview/download/delete, and ZIP Validate Project / download report. Check AI Chat remains unchanged. Test on narrow screens.

The installer creates timestamped backups before applying. If your current `App.tsx` differs from the expected section anchors, it stops without modifying anything. No database migrations or backend / worker restart needed.

## Limitations

Visual appearance has not been verified inside your browser or your local Docker build. This release is scoped to layout/contrast improvements and does not add new product features.

## Custom heading fix
This installer version identifies the Knowledge Base section using the **Upload knowledge document** control, not the literal `Phase 2 · Knowledge Base` heading. Your customized heading is preserved.
