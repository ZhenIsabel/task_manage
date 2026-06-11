# AI Repository Guide

This file applies to the repository root and every descendant directory.

## Required Reading

Before changing code, read only `docs/AI_PROJECT_MAP.md` first. It is the
lightweight routing index for the project map.

Use its task-routing table to open the 1-3 relevant files under
`docs/ai-project-map/`. Do not load all project-map volumes by default. A
typical focused task needs the index and one primary volume; add related
volumes only when the change crosses subsystem boundaries.

The existing `README.md` contains useful product background, but parts of its
directory tree, server description, and launch instructions are historical.
When documentation disagrees with executable code, verify the code and update
the relevant `docs/ai-project-map/` volume plus the index if routing or scope
has changed.

## Project Snapshot

- Windows-oriented Python desktop task manager built with PyQt6 and
  PyQt6-Fluent-Widgets.
- `main.py` creates the application and the main `QuadrantWidget`.
- `windows/tray_launcher.py` is the Windows tray wrapper and launches
  `main.py` in a separate process.
- `core/quadrant_widget.py` is the main UI and workflow coordinator.
- `database/database_manager.py` owns SQLite persistence, in-memory caches,
  history, background flush, and optional remote synchronization.
- `config/` owns application and remote-sync configuration.
- `ui/` contains shared visual primitives, styles, notifications, Fluent
  compatibility helpers, scroll areas, badges, and adaptive tables.
- `gantt/` is an optional Flask/Frappe Gantt view that reads SQLite directly.
- `tests/` contains the regression suite. Match changes to the test map in
  `docs/ai-project-map/07-dependencies-tests.md`.

## Repository Rules

- On Windows, use PowerShell 7 (`pwsh`), never Windows PowerShell 5.1, for file
  writes.
- Prefer direct editing tools. If a shell write is unavoidable, specify UTF-8
  explicitly with `Set-Content`, `Add-Content`, or `Out-File`.
- Preserve an existing file's newline style and encoding when practical.
- Do not edit SQLite databases, database backups, logs, caches, virtual
  environments, `.tmp-tests/`, or `.worktrees/` as source code.
- Do not copy, print, commit, or expose values from `LLM_CONFIG.api_key`,
  `api_token`, usernames, or private service URLs. Configuration files in a
  working tree may contain live credentials.
- Do not bypass `get_db_manager()` with a new database connection in desktop
  features. The existing Gantt reader is a documented exception.
- Preserve logical deletion, task history, cache locking, dirty flags,
  periodic flush, and remote-sync behavior when changing persistence code.
- Task quadrant meaning is spatial: right means high urgency and top means high
  importance. Any position or layout change must preserve or deliberately
  migrate that contract.
- Reuse `ui.notifications`, `ui.styles`, `ui.fluent`, `ui.scrollbar`, and
  `ui.adaptive_table` instead of introducing parallel UI conventions.
- Keep user-facing Chinese text and existing non-ASCII content intact.

## Change Workflow

1. Read `docs/AI_PROJECT_MAP.md`, then only the volumes routed for the task.
2. Inspect the listed callers, dependencies, configuration keys, and tests.
3. Check `git status` and preserve unrelated user changes.
4. Make the smallest change consistent with existing patterns.
5. Run the focused tests listed in the impact matrix.
6. Run the full suite for shared UI, configuration, database, or sync changes.
7. Update the relevant project-map volume when changing directories, entry
   points, imports, dependencies, database schema, configuration contracts,
   runtime flows, or test ownership. Update `docs/AI_PROJECT_MAP.md` as well
   when the task routing or volume scope changes.

## Verification

From the repository root, the preferred full-suite command is:

```powershell
& '.\venv\Scripts\python.exe' -m unittest discover -s tests -v
```

For a focused module:

```powershell
& '.\venv\Scripts\python.exe' -m unittest tests.test_module_name -v
```

PyQt tests may configure an offscreen platform internally. Do not assume a
visual change is correct from unit tests alone; perform a targeted UI check
when the rendered result or interaction behavior changes.
