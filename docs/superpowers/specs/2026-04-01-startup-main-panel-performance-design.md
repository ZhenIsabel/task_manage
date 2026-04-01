# Startup and Main Panel Performance Design

Date: 2026-04-01

## Background

The app currently feels slow when opening the main window.

Two concrete causes are visible in the current implementation:

1. `QuadrantWidget` schedules startup remote sync immediately, and that path performs remote health check plus remote pulls on the UI thread.
2. `QuadrantWidget.load_tasks()` creates one `TaskLabel` per task, and each `TaskLabel` reloads task field config from disk during construction.

In this workspace, local task volume is already enough to amplify avoidable hot spots:

- `tasks`: 193
- `task_history`: 2448

## Goals

Reduce user-perceived latency when opening the main window without changing task semantics or remote sync semantics.

The new behavior must ensure that:

- the main window can render local tasks before remote bootstrap completes,
- remote bootstrap no longer blocks the UI thread,
- bulk task widget creation avoids repeated config file reads,
- bulk task widget creation reduces unnecessary intermediate repaint work.

## Non-Goals

This work does not aim to:

- redesign the sync model,
- change scheduled-task panel behavior,
- replace the current widget architecture,
- change sorting, filtering, or task visuals.

## Options Considered

### Option A: Only lower remote request timeout

Pros:

- Small change.

Cons:

- Still blocks the UI thread.
- Does not address local widget build cost.

### Option B: Only make startup sync asynchronous

Pros:

- Removes the largest startup freeze.

Cons:

- Leaves repeated config loads during main-panel rebuild untouched.

### Option C: Combine async startup sync with main-panel build-path cleanup

Pros:

- Removes both the remote and local startup hot spots.
- Keeps behavior stable.

Cons:

- Slightly larger change surface than Option B.

## Chosen Approach

Use Option C.

## Design

### Background startup sync

`QuadrantWidget._bootstrap_remote_sync()` will keep validation on the UI thread, but the blocking call to `DatabaseManager.bootstrap_remote_sync()` will move to a daemon thread.

The flow becomes:

1. If the widget is closing or remote sync is disabled, return.
2. If username or token is missing, keep the current warning behavior.
3. Start a background thread for the blocking bootstrap sync.
4. Emit the result back to the UI thread with a Qt signal.
5. Refresh tasks on the UI thread only after successful completion.

### Main-panel task build optimization

`TaskLabel` will cache editable field metadata at the class level and accept preloaded field definitions from callers.

`QuadrantWidget.load_tasks()` will:

- fetch task data once,
- reuse preloaded field definitions,
- disable updates while clearing and rebuilding task widgets,
- re-enable updates after the batch is complete.

This keeps behavior the same while cutting repeated file I/O and repaint churn.

## Testing Strategy

### Automated tests

Cover:

1. startup bootstrap starts background work instead of calling `bootstrap_remote_sync()` inline,
2. missing remote username still shows the current warning and does not start background work,
3. `TaskLabel.get_editable_fields()` uses cached config instead of reloading repeatedly,
4. `QuadrantWidget.load_tasks()` batches updates while rebuilding the task list.

### Manual verification

1. Start the app with remote sync enabled and confirm the main window appears with local tasks before remote bootstrap finishes.
2. Simulate slow or unavailable remote service and confirm the UI remains responsive.
3. Confirm that remote bootstrap success still refreshes task data.

## Risks and Mitigations

### Risk 1: Background thread finishes after widget close

Mitigation:

- guard completion with `_is_closing`,
- deliver UI refresh through a Qt signal on the main thread.

### Risk 2: Cached field definitions become stale during runtime

Mitigation:

- prefer caller-provided field definitions on the main load path,
- keep config-based fallback for other call sites.

## Acceptance Criteria

This work is complete when:

1. startup remote bootstrap no longer runs blocking network work on the UI thread,
2. local tasks can render before remote bootstrap finishes,
3. `TaskLabel` no longer reloads config per task during bulk main-panel load,
4. `QuadrantWidget.load_tasks()` rebuilds tasks with update batching,
5. existing missing-config warning behavior remains intact.
