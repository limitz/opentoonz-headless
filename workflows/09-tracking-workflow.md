# OpenToonz Tracking/Match-Move Workflow

Extracted from the OpenToonz source code -- a pipeline for tracking object/camera motion from footage.

---

## Overview

OpenToonz includes a basic optical tracking system for following objects across frames. Users define tracking regions on the canvas, and the tracker computes motion between consecutive frames. Results can be applied as keyframes to XSheet columns.

---

## Step 1: Define Tracking Regions

**Source:** `toonz/sources/tnztools/trackertool.cpp`

Using the **Tracker Tool**, draw rectangular regions around objects to track. Each region maps to an object ID (max 30 simultaneous objects).

---

## Step 2: Configure Tracking Parameters

**Source:** `toonz/sources/toonz/trackerpopup.cpp`

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| Threshold | 0.0-1.0 | 0.2 | Match confidence threshold |
| Sensitivity | 0-1000 | 10 | Tracking responsiveness (scaled to 0-1) |
| Variable Region | Boolean | false | Adaptive tracking box size |
| Include Background | Boolean | false | Background-aware tracking |

---

## Step 3: Execute Tracking

### Key Classes

- **Tracker** -- core tracking engine with `CObjectTracker[30]` array
- **MyThread** (QThread) -- async execution

### Process

1. `setup()` -- initialize tracker with region templates
2. For each frame pair (current -> next):
   - Compare raster template against current frame
   - Compute affine transform for region movement
   - Update tracker positions
3. Stop after target frame or on cancellation

---

## Step 4: Apply Results

Tracked motion is converted to keyframes applied to XSheet column stage objects (position, rotation, scale).

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Tracker UI | `trackerpopup.cpp` | Settings and execution |
| Tracker Tool | `trackertool.cpp` | Interactive region selection |
| Track Core | `track.cpp` | Tracking algorithm |

---

## Headless API Gaps

1. **Region definition** -- define tracking boxes programmatically
2. **Tracker execution** -- run tracking across frame range
3. **Result extraction** -- get motion data as keyframe arrays
4. **Keyframe application** -- apply tracked motion to stage objects
