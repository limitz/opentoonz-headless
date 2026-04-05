# OpenToonz Character Design Workflow

Extracted from the OpenToonz source code — a step-by-step pipeline for creating characters ready for animation.

---

## Overview

OpenToonz treats character creation as a **level-based system**. A "level" is a collection of frame images (drawings) that share a palette and properties. Characters are built by creating levels, drawing on them with specialized tools, coloring via palettes and fill tools, and organizing frames in the XSheet (timeline).

---

## Step 1: Create a Character Level

**Menu:** File → New Level (`MI_NewLevel`, Alt+N)
**Source:** `toonz/sources/toonz/levelcreatepopup.cpp`

Choose a level type based on your art style:

| Type | Format | Best For |
|------|--------|----------|
| **Toonz Vector (PLI)** | Vector strokes + regions | Clean linework, scalable art, cut-out rigs |
| **Toonz Raster (TZP)** | Indexed-color raster (ink/paint/tone channels) | Traditional cel-style animation, cleanup |
| **Raster (OVL)** | Full-color RGBA | Painted/textured characters, concept art |
| **Assistants (META)** | Guide/reference layer | Construction lines, perspective guides |

**Parameters to set:**
- Name and frame range (From, To, Step, Increment)
- Canvas size (width/height) and DPI
- Output format (TIF/PNG for raster levels)

The level is added to the scene's LevelSet and cells are created in the XSheet.

---

## Step 2: Set Up a Color Model (Reference)

**Source:** `toonz/sources/toonz/colormodelviewer.cpp`

Load a reference image that serves as the character's **model sheet**:

1. Open the Color Model viewer (a FlipBook-based panel)
2. Load an image from disk or use the current frame
3. The reference is stored in the palette metadata

**Pick modes:**
- Areas only — sample fill colors
- Lines only — sample ink/outline colors
- Lines & Areas — sample both

Tools can then pick colors/styles directly from the reference image, ensuring palette consistency.

---

## Step 3: Build the Palette

**Source:** `toonz/sources/toonzlib/palettecontroller.h`

OpenToonz uses three palette scopes:

- **Level Palette** — colors specific to one level (embedded in the level file)
- **Studio Palette** — shared across the entire studio/project
- **Cleanup Palette** — specialized for scan cleanup operations

For character design, the **Level Palette** is primary. Each color entry (style) has an index used by both vector strokes and TZP raster channels. This separation of color definition from drawing data allows global recoloring.

---

## Step 4: Draw the Character

**Source:** `toonz/sources/tnztools/`

### Primary Drawing Tools

**Brush (Vector)** — `toonzvectorbrushtool.cpp`
- Min/max thickness with pressure sensitivity
- Acceleration, smoothing, break angle controls
- Cap/join/miter stroke styles
- Preset system (`VectorBrushData`)

**Brush (Raster)** — `toonzrasterbrushtool.cpp`
- Min/max size, hardness, opacity
- Pencil mode (aliased) vs. smooth mode
- MyPaint brush engine support
- Draw order control, lock-alpha modifier
- Preset system (`BrushData`)

**Geometric Tool** — `geometrictool.cpp`
- Rectangles, circles, ellipses, polygons, lines, arcs
- Edge count, rotation, auto-group, auto-fill, snap

### How Drawing Works Internally

```
Tablet/mouse input
  → TTool::leftButtonDown / Drag / Up
    → StrokeGenerator accumulates TThickPoints (position + pressure)
      → Vector: new TStroke added to TVectorImage
      → Raster: RasterStrokeGenerator renders pixels to tile buffer
        → TUndo records the operation
          → Viewer invalidates affected region
```

---

## Step 5: Fill and Color the Character

**Source:** `toonz/sources/tnztools/filltool.cpp`, `paintbrushtool.cpp`

### Fill Tool
- **Selection modes:** Click (flood), Rect, Polyline, Freehand
- **Targets:** Lines (ink), Areas (paint), or both
- **Options:** Selective (empty areas only), auto-paint, frame-range filling
- Supports onion-skin preview for multi-frame batch fills

### Paint Brush Tool
- Paints lines or areas with a brush stroke
- Selective mode to only paint empty regions
- Useful for touch-ups after automatic fills

### Style Picker Tool
- Pick colors/styles from existing artwork or the color model
- Feeds into the palette controller for quick color switching

---

## Step 6: Use Onion Skin for Consistency

**Source:** `toonz/sources/include/toonz/onionskinmask.h`

Onion skin overlays adjacent frames semi-transparently so you can maintain proportion and pose consistency across drawings.

**Two modes:**
- **MOS (Mobile Onion Skin)** — Relative offsets from current frame (e.g., -2, -1, +1, +2)
- **FOS (Fixed Onion Skin)** — Always show specific frame numbers (e.g., frame 1 = base pose)

**Shift & Trace** — Advanced mode for precise registration:
- `ENABLED` — Show ghost frames that can be repositioned
- `EDITING_GHOST` — Interactively move/rotate ghost frames
- `ENABLED_WITHOUT_GHOST_MOVEMENTS` — Show without transforms

Fade is calculated by distance: `getOnionSkinFade(distance)` returns opacity.

---

## Step 7: Manage Frames and Drawings

**Source:** `toonz/sources/toonzlib/drawingdata.h`, `txshcell.h`

### Frame ID System
- Numeric: 1, 2, 3, 4...
- Suffixed: 1a, 1b, 1c... (for breakdowns/inbetweens)
- Auto-increment with smart suffix handling

### Drawing Operations
- **INSERT** — Add new frames, shifting existing ones down
- **OVER_FRAMEID** — Replace frames with the same ID
- **OVER_SELECTION** — Replace currently selected frames
- Duplicate frames for variations (preserves fills and hooks)

### XSheet Cell Structure
Each cell = `TXshLevel` pointer + `TFrameId`. Cells can be empty, hold a unique drawing, or repeat a drawing (frame hold).

---

## Step 8: Organize in the XSheet

**Source:** `toonz/sources/include/toonz/txsheet.h`

The XSheet (exposure sheet / timeline) is where character elements are assembled:

- **Level Columns** — One per character part or drawing layer
- **Column stacking** — Controls draw order (back to front)
- **Frame exposure** — How many frames each drawing is held

For a multi-part character (e.g., cut-out style):
```
Column 1: Head level
Column 2: Body level
Column 3: Left arm level
Column 4: Right arm level
Column 5: Legs level
```

Each column references a level and maps frames to cells in the timeline.

---

## Step 9: Animate with Keyframes & Interpolation

**Source:** `toonz/sources/include/tdoublekeyframe.h`, `toonz/sources/include/toonz/tstageobject.h`

Not every frame needs to be hand-drawn. Each stage object (column/pegbar) has **10 animatable channels**: position (X, Y, Z), rotation, scale (X, Y), shear, stacking order, and path position. Set values at key frames and OpenToonz interpolates between them.

### Interpolation Types

| Type | Description |
|------|-------------|
| **Constant** | Hold value until next keyframe |
| **Linear** | Straight-line interpolation |
| **SpeedInOut** | Cubic Bezier with tangent handles |
| **EaseInOut** | Parametric easing curves |
| **EaseInOutPercentage** | Percentage-based easing |
| **Exponential** | Exponential interpolation |
| **Expression** | Formula-driven (can reference other params) |
| **File** | Loaded from external data |
| **SimilarShape** | References another curve with offset |

Curves are edited in the **Function Editor** (`toonzqt/functionpanel.cpp`) — a graph view with draggable Bezier handles plus a spreadsheet view for precise numeric entry.

---

## Step 10: Rig with Bones (Cut-Out Animation)

**Source:** `toonz/sources/tnztools/skeletontool.cpp`, `toonz/sources/include/toonz/ikskeleton.h`

For cut-out style characters (body parts on separate columns), the **Skeleton Tool** builds a bone hierarchy:

- Bones link to XSheet columns via the stage object tree
- **Hooks** (attachment points on drawings) connect limbs across columns
- Pose the character at key frames; transforms interpolate automatically

### Inverse Kinematics

**Source:** `ikengine.h`, `ikjacobian.h`

Four IK solving methods:
1. **Jacobian Transpose** — simplest, less accurate
2. **Pseudo-Inverse** — more stable
3. **Damped Least Squares (DLS)** — reduces numerical instability
4. **Selective DLS (SDLS)** — per-joint damping

Drag an end effector (e.g., a hand) and the IK solver computes all joint angles up the chain. Joints can be pinned/locked via `TPinnedRangeSet`.

---

## Step 11: Deform with Plastic (Mesh Deformation)

**Source:** `toonz/sources/tnztools/plastictool.cpp`, `toonz/sources/include/ext/plasticdeformer.h`

For smooth shape changes without redrawing (squash/stretch, head turns, fabric):

1. Overlay a **triangulated mesh** on a drawing
2. Place control vertices with parent-child relationships
3. Each vertex has 3 animatable parameters:
   - **Angle** — rotation relative to parent
   - **Distance** — distance from parent vertex
   - **Stacking Order** — depth sorting
4. Keyframe the vertices → mesh deforms smoothly between poses

Uses barycentric coordinate interpolation across triangular faces. Multiple skeleton configurations can be swapped on the same timeline.

---

## Step 12: Auto-Inbetween Vector Drawings

**Source:** `toonz/sources/include/tinbetween.h`

For **vector levels (PLI) only**, OpenToonz can automatically generate intermediate drawings between two key drawings:

```
Key Drawing A  →  tween(0.25)  →  tween(0.5)  →  tween(0.75)  →  Key Drawing B
```

- `tween(t)` interpolates all strokes and shapes (t ∈ [0, 1])
- Modes: **Linear**, **EaseIn**, **EaseOut**, **EaseInOut**
- Uses corner detection and weighted averaging for intelligent blending
- This creates actual new frame images — true drawing interpolation

---

## Step 13: Animate Along Motion Paths

**Source:** `toonz/sources/include/toonz/tstageobjectspline.h`

Constrain a stage object to follow a Bezier spline curve:

1. Draw a motion path (spline) in the scene
2. Set the stage object's status to **PATH** or **PATH_AIM**
3. Animate the `T_Path` parameter from 0% → 100%
4. **PATH_AIM** mode auto-rotates the object to match the curve tangent

Splines use length-normalized parameterization for constant velocity. Editing the spline can auto-update keyframes (UPPK mode).

---

## Step 14: Add Particle Effects

**Source:** `toonz/sources/stdfx/particlesfx.h`, `particlesengine.h`

Fully procedural animated effects — no hand-drawing needed:

- **Physics:** gravity (angle + force), wind, friction, swing oscillation
- **Per-particle:** position, velocity, scale, rotation, opacity, lifetime, trail
- **Animation modes:** Hold, Random, Cycle with configurable step
- **Color:** generate/finish colors with spectrum-based gradients
- All parameters are keyframeable

---

## Automation Summary

| Technique | What It Automates | Level Type | Source |
|-----------|-------------------|------------|--------|
| Keyframe interpolation | Position, rotation, scale, shear | All | `tdoublekeyframe.h` |
| Bone/Skeleton rig | Cut-out character posing with IK | All (column-based) | `skeletontool.cpp` |
| Plastic deformation | Mesh-based shape changes | All | `plastictool.cpp` |
| Auto-inbetweening | Intermediate vector drawings | Vector (PLI) only | `tinbetween.h` |
| Motion paths | Movement along curves | All | `tstageobjectspline.h` |
| Particle effects | Procedural VFX | N/A (effect layer) | `particlesfx.h` |
| Expression params | Formula-driven animation | All | `tdoubleparam.h` |

---

## Data Flow Summary

```
Project
 └── Scene (.tnz)
      ├── XSheet (timeline)
      │    └── Columns → Cells (Level + FrameId)
      ├── LevelSet
      │    └── Levels (.pli / .tlv / .png)
      │         ├── Frames (drawings)
      │         └── Palette (color styles)
      └── Scene Properties
           ├── Frame rate, resolution
           ├── Background color
           └── Field guide settings
```

---

## File Format Reference

| Extension | Type | Contents |
|-----------|------|----------|
| `.tnz` | Scene | XSheet, level references, scene properties |
| `.pli` | Toonz Vector Level | Vector strokes, regions, style indices |
| `.tlv` | Toonz Raster Level | Indexed-color tiles (ink/paint/tone) |
| `.tpl` | Toonz Palette | Color style definitions |
| `.png/.tif` | Raster Level frames | Full-color images |

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Level Creation | `levelcreatepopup.cpp` | New level dialog |
| Level Types | `txshleveltypes.h` | Type enum definitions |
| Vector Brush | `toonzvectorbrushtool.cpp` | PLI drawing tool |
| Raster Brush | `toonzrasterbrushtool.cpp` | TZP/OVL drawing tool |
| Geometric | `geometrictool.cpp` | Shape primitives |
| Fill | `filltool.cpp` | Flood/area fill |
| Palette | `palettecontroller.h` | Color management |
| Color Model | `colormodelviewer.cpp` | Reference image viewer |
| Onion Skin | `onionskinmask.h` | Multi-frame overlay |
| XSheet | `txsheet.h` | Timeline structure |
| Image Manager | `imagemanager.h` | Image caching/threading |
| Stroke Gen | `strokegenerator.h` | Input → path conversion |
| Keyframes | `tdoublekeyframe.h` | Keyframe data & interpolation types |
| Animation Curves | `tdoubleparam.h` | Animatable parameter curves |
| Function Editor | `functionpanel.cpp` | Curve graph editor UI |
| Stage Object | `tstageobject.h` | Transform channels & hierarchy |
| Skeleton Tool | `skeletontool.cpp` | Bone rig & IK interaction |
| IK Engine | `ikengine.h`, `ikjacobian.h` | Inverse kinematics solver |
| Plastic Tool | `plastictool.cpp` | Mesh deformation UI |
| Plastic Deformer | `plasticdeformer.h` | Mesh deformation algorithm |
| Auto-Inbetween | `tinbetween.h` | Vector frame interpolation |
| Motion Paths | `tstageobjectspline.h` | Spline-based movement |
| Particles | `particlesfx.h` | Procedural particle effects |
