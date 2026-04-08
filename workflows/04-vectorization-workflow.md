# OpenToonz Vectorization Workflow

Extracted from the OpenToonz source code -- a step-by-step pipeline for converting raster artwork to scalable vector format.

---

## Overview

The vectorizer converts raster drawings (scanned or digital) into vector strokes (PLI format). Two algorithms are available: **Centerline** (extracts medial axis skeleton with variable thickness) and **Outline** (traces contour boundaries). Both support color recognition, despeckling, and per-frame parameter interpolation.

---

## Step 1: Choose Vectorization Mode

**Source:** `toonz/sources/include/toonz/vectorizerparameters.h`

### Centerline Mode

Extracts the **medial axis skeleton** of brushstrokes. Output strokes have variable thickness encoding the original stroke width.

**Best for:** Inked line art, pencil drawings, clean linework.

### Outline Mode

Traces **contour boundaries** of shapes. Output strokes are uniform-thickness outlines.

**Best for:** Filled shapes, painted artwork, complex color regions.

---

## Step 2: Configure Parameters

### Base Parameters (both modes)

| Parameter | Range | Description |
|-----------|-------|-------------|
| `m_threshold` | 0-255 | Ink/background tone threshold |
| `m_leaveUnpainted` | Boolean | Skip fill color computation (inverted in UI as "Paint Fill") |
| `m_alignBoundaryStrokesDirection` | Boolean | Align strokes clockwise |

### Centerline Configuration

**Source:** `toonz/sources/include/toonz/tcenterlinevectorizer.h`

| Parameter | UI Range | Internal | Default | Description |
|-----------|----------|----------|---------|-------------|
| Threshold | 0-8 | x25 -> 0-200 | 200 | Ink/paper distinction |
| Accuracy | 1-10 | penalty = 10-accuracy | 7 | Simplicity vs. fidelity tradeoff |
| Despeckling | 0-100 | x2 -> 0-200 | 10 | Min region area to keep (pixels) |
| Max Thickness | 0-200+ | /2.0 | 100 | Max stroke thickness (0 = outline only) |
| Thickness Ratio | 0-200% | direct | 100% | Post-processing thickness scale |
| Paint Fill | Boolean | inverted | true | Compute fill regions |
| Make Frame | Boolean | direct | false | Add border rectangle |
| NAA Source | Boolean | direct | false | Enhanced ink recognition for full-color |

### Outline Configuration (New)

**Source:** `toonz/sources/include/tnewoutlinevectorize.h`

| Parameter | UI Range | Internal | Default | Description |
|-----------|----------|----------|---------|-------------|
| Accuracy | 0-10 | mergeTol = 5-acc*0.5 | 7 | Curve simplification vs. fidelity |
| Despeckling | 0-200+ | direct | 4 | Edge despeckling (n x n pixels) |
| Adherence | 0-100 | x0.01 -> 0-1 | 50 | Corner following tolerance |
| Angle | 0-180 | /180 -> 0-1 | 45 | Angle-based corner detection (degrees) |
| Curve Radius | 0-100 | x0.01 -> 0-1 | 25 | Curvature-based corner detection |
| Max Colors | 1-256 | direct | 50 | Color quantization limit (fullcolor) |
| Transparent Color | RGB | TPixel32 | White | Color recognized as transparent |
| Tone Threshold | 0-255 | direct | 128 | TLV grayscale threshold |
| Paint Fill | Boolean | inverted | true | Compute fill regions |

---

## Step 3: Prepare Input

### Supported Input Formats

| Type | Class | Use Case |
|------|-------|----------|
| Full-color raster | TRasterImage (32-bit RGBA) | Photos, painted artwork |
| Toonz raster | TToonzImage (colormap) | Native Toonz levels |
| NAA full-color | TToonzImage + naaSource | Retas-style non-antialiased paintings |
| Grayscale | TRasterGR8 | Ink-only scans |

### DPI Handling

The vectorizer applies a DPI transformation affine to convert from pixel coordinates to stage coordinates. Default DPI is 65.0 if not specified.

---

## Step 4: Execute Vectorization

**Source:** `toonz/sources/toonzlib/toutlinevectorizer.cpp` (entry point)

### Main Entry Point

```cpp
TVectorImageP VectorizerCore::vectorize(
    const TImageP &img,
    const VectorizerConfiguration &config,
    TPalette *palette
);
```

Routes to `centerlineVectorize()` or `newOutlineVectorize()` based on `config.m_outline`.

---

## Step 5: Centerline Algorithm

**Source:** `toonz/sources/toonzlib/tcenterline*.cpp`

### Processing Pipeline

```
Input Raster
    |
    v
[1] Polygonization (contour extraction)
    - Extract outlines from thresholded image
    - Build polygon representation
    |
    v
[2] Skeletonization (most CPU-intensive step)
    - Calculate medial axis skeleton
    - Uses topological thinning
    - Emits partial progress notifications
    |
    v
[3] Skeleton Graph Organization
    - organizeGraphs(skeletons)
    - Build graph data structure from skeleton
    |
    v
[4] Color Extraction
    - calculateSequenceColors(raster)
    - Sample ink colors from original image at skeleton positions
    |
    v
[5] Conversion to Strokes
    - conversionToStrokes(sortableResult)
    - Fit Bezier curves to skeleton paths
    - Encode thickness from skeleton distance field
    |
    v
[6] Stroke Color Application
    - applyStrokeColors(strokes, raster, palette)
    - Assign palette style IDs to strokes
    |
    v
[7] Post-Processing
    a) Thickness reduction (if thicknessRatio < 100%)
    b) Self-loop conversion (if maxThickness == 0)
    c) Frame border addition (if makeFrame = true)
    |
    v
Output TVectorImage
```

### Key Data Structures

- **ContourNode** -- vertex with position + direction + thickness (3D: z = thickness)
- **Graph<NodeContent, ArcType>** -- directed graph with local link storage
- **SkeletonList** -- vector of skeleton graphs (one per connected region)

---

## Step 6: Outline Algorithm

**Source:** `toonz/sources/toonzlib/tnewoutlinevectorize.cpp`

### Processing Pipeline

```
Input Raster
    |
    v
[1] Border/Edge Analysis
    - Gradient computation per pixel
    - Edge linking in 8 directions
    |
    v
[2] Contour Tracing
    - Follow outline boundaries
    - Build proto-outlines (deques of TThickPoint)
    |
    v
[3] Junction Detection & Resolution
    - Identify multi-way intersections
    - Calculate junction centers
    - Lock convex junctions
    |
    v
[4] Stroke Fitting
    - Fit quadratic/Bezier curves
    - Apply corner tolerance parameters (adherence, angle, curve radius)
    - mergeTol controls curve simplification
    |
    v
[5] Color Quantization (fullcolor input)
    - K-means style quantization
    - Limit to maxColors
    - Transparent color recognition
    |
    v
[6] Palette Building
    - Create output palette from quantized colors
    |
    v
Output TVectorImage
```

---

## Step 7: Batch Processing

**Source:** `toonz/sources/toonz/vectorizerpopup.cpp`

### Per-Frame Parameter Interpolation

The vectorizer supports interpolating parameters across a frame range:

```
weight = (current_frame - first_frame) / (last_frame - first_frame)
weight = clamp(weight, 0.0, 1.0)

thicknessRatio = (1 - weight) * firstFrameRatio + weight * lastFrameRatio
```

This allows gradual thickness changes across a sequence.

### Batch Flow

1. User selects raster level and frame range
2. New vector level (PLI) is created
3. For each frame:
   - Retrieve full-sampled frame image
   - Apply DPI transformation
   - Calculate interpolated parameters
   - Call `VectorizerCore::vectorize()`
   - Store result: `vectorLevel.setFrame(fid, vectorImage)`
4. Progress reporting via signals
5. Cancellation supported (breaks loop, cleans up)

---

## Output Format

### TVectorImage Structure

- Collection of `TStroke` objects
- Each stroke has:
  - Control points with thickness (TThickPoint = x, y, thickness)
  - Style ID (reference to palette)
  - Attributes (self-loop flag, etc.)
- Computed regions (for fill color assignment)
- Associated TPalette

### Centerline vs. Outline Output

| Aspect | Centerline | Outline |
|--------|-----------|---------|
| Stroke meaning | Medial axis | Contour boundary |
| Thickness | Variable (encodes width) | Uniform |
| Color source | Sampled from input | Quantized or mapped |
| Fill regions | Computed from intersections | Computed from boundaries |
| Frame border | Optional (makeFrame) | N/A |

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Parameters | `vectorizerparameters.h` | All config classes |
| Core Entry | `toutlinevectorizer.cpp:1612` | VectorizerCore::vectorize() dispatcher |
| Centerline | `tcenterlinevectorizer.cpp` | Main centerline entry (235 lines) |
| Polygonizer | `tcenterlinepolygonizer.cpp` | Contour extraction |
| Skeletonizer | `tcenterlineskeletonizer.cpp` | Medial axis (70KB, most complex) |
| Colors | `tcenterlinecolors.cpp` | Color extraction |
| Strokes | `tcenterlinetostrokes.cpp` | Skeleton -> stroke conversion |
| Adjustments | `tcenterlineadjustments.cpp` | Post-processing |
| New Outline | `tnewoutlinevectorize.cpp` | New outline algorithm |
| Private Types | `tcenterlinevectP.h` | Internal data structures |
| Batch UI | `vectorizerpopup.cpp` | Batch processing orchestration |

---

## Headless API Gaps

The current headless API has **no vectorization functionality**. Everything needed:

1. **Vectorizer object** -- expose VectorizerCore with mode selection
2. **Centerline config** -- threshold, accuracy, despeckling, max thickness, thickness ratio
3. **Outline config** -- accuracy, despeckling, adherence, angle, curve radius, max colors
4. **Input handling** -- accept ToonzRaster or Raster images
5. **Palette integration** -- use existing palette or auto-generate
6. **Batch processing** -- vectorize multiple frames with parameter interpolation
7. **Progress/cancel** -- report progress, support cancellation
8. **Output** -- return TVectorImage for use with existing Level API
