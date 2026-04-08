# OpenToonz Batch/Farm Workflow

Extracted from the OpenToonz source code -- a pipeline for queuing and distributing render/cleanup tasks.

---

## Overview

OpenToonz supports batch processing via a task queue system. Tasks (render or cleanup) are defined as serializable `TFarmTask` objects, queued in a `BatchesController`, and executed locally via `TaskRunner` or distributed across a network farm via `TFarmController`.

---

## Step 1: Create Tasks

**Source:** `toonz/sources/include/tfarmtask.h`

### TFarmTask Properties

| Property | Type | Description |
|----------|------|-------------|
| `m_id` | Id | Auto-generated unique identifier |
| `m_name` | QString | User-specified task name |
| `m_taskFilePath` | TFilePath | Scene file (TNZ) or cleanup file (CLN) |
| `m_outputPath` | TFilePath | Render destination |
| `m_from, m_to, m_step` | int | Frame range |
| `m_shrink` | int | Output resolution reduction factor |
| `m_chunkSize` | int | Frames per subtask (for parallelization) |
| `m_dependencies` | Dependencies* | Task dependency graph |
| `m_status` | TaskState | Queued / Running / Completed / Aborted |

### Task Types

| Type | Description | Tool |
|------|-------------|------|
| Render | Render TNZ scene to output | `tcomposer` |
| Cleanup | Process CLN cleanup settings | `tcleanup` |

---

## Step 2: Configure Task Queue

**Source:** `toonz/sources/toonz/batches.cpp`

### BatchesController (singleton)

- `addComposerTask(scenePath, outputPath, frameRange)` -- add render task
- `addCleanupTask(cleanupPath)` -- add cleanup task
- `doSave(path)` / `doLoad(path)` -- save/load batch list (TNZBAT XML)

### Task Groups

`TFarmTaskGroup` bundles subtasks:
- `addTask(task)` / `removeTask(task)`
- `changeChunkSize(newSize)` -- re-subdivide frames

---

## Step 3: Execute Tasks

### Local Execution

`TaskRunner` (QThread) executes tasks sequentially:

1. Check dependencies (execute prerequisites first)
2. Generate command: `tcomposer -tnz [file] -frames [from-to-step] -o [output]`
3. Launch via QProcess
4. Monitor exit code
5. Update status: Running -> Completed/Aborted

### Farm Execution

**Source:** `toonz/sources/toonzfarm/`

| Component | Port | Purpose |
|-----------|------|---------|
| TFarmController | 51005 | Central task distribution |
| TFarmServer | varies | Worker node (renders assigned chunks) |

Farm distributes chunks across available servers with automatic load balancing.

---

## Step 4: Monitor and Collect Results

### Task States

| State | Description |
|-------|-------------|
| Queued | Waiting in queue |
| Running | Currently executing |
| Completed | Finished successfully |
| Aborted | Failed or cancelled |

### Batch File Format

TNZBAT files are XML-serialized `TFarmTaskGroup` objects containing all task metadata and dependency graphs. Portable across machines.

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Batches | `batches.cpp` | Task queue management |
| Farm Task | `tfarmtask.h` | Task definition |
| Task Runner | Internal in batches.cpp | Local execution |
| Farm Server | `toonzfarm/` | Network distribution |
| Batch UI | `batchserversviewer.cpp` | Server monitoring |
| Save/Load | `batches.cpp` | TNZBAT XML serialization |

---

## Headless API Gaps

1. **Task creation** -- define render/cleanup tasks programmatically
2. **Queue management** -- add, remove, reorder tasks
3. **Dependency graph** -- set task prerequisites
4. **Local execution** -- run tasks synchronously or async
5. **Progress monitoring** -- track task status and completion
6. **TNZBAT I/O** -- save/load batch lists
