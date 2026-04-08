# OpenToonz Scan/Cleanup Workflow

Extracted from the OpenToonz source code -- a step-by-step pipeline for processing scanned paper artwork into clean digital levels.

---

## Overview

The cleanup pipeline transforms raw scanned drawings into production-ready digital frames. It handles geometric alignment (registration via pegbar holes), tonal normalization (auto-adjust), color recognition (ink/paint separation), and post-processing (despeckling, antialiasing). The output is a Toonz ToonzImage (colormap format) with a linked palette.

---

## Step 1: Scan Paper Artwork

**Source:** `toonz/sources/toonz/scanpopup.cpp`

### Scanner Settings

| Setting | Options | Description |
|---------|---------|-------------|
| Driver | TWAIN / Internal | Scanner interface |
| Paper Format | A3, A4, B4, B5, etc. | Scan area |
| Reverse Order | Boolean | Reverse page sequence |
| Paper Feeder | Boolean | Use ADF (auto document feeder) |
| Output Mode | BW / Graytones / RGB Color | Scan color depth |
| DPI | 72-600+ | Scan resolution |
| Threshold | 0-255 | BW mode: ink/paper cutoff |
| Brightness | -100 to 100 | Graytone/Color: tonal shift |

### Data Flow

```
Scanner -> Raw TRaster32P or TRasterGR8P
        -> Stored as temporary raster level
```

---

## Step 2: Configure Cleanup Parameters

**Source:** `toonz/sources/include/toonz/cleanupparameters.h`

### Geometric Alignment

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `m_autocenterType` | NONE, FDG, CTR | NONE | Registration method |
| `m_pegSide` | BOTTOM, TOP, LEFT, RIGHT | BOTTOM | Pegbar hole location |
| `m_rotate` | 0, 90, 180, 270 | 0 | Page rotation (degrees) |
| `m_flipx` | Boolean | false | Horizontal flip |
| `m_flipy` | Boolean | false | Vertical flip |
| `m_offx, m_offy` | Double | 0.0 | X/Y offset |

### Camera & Scaling

| Parameter | Description |
|-----------|-------------|
| `m_camera` | TCamera instance (resolution + physical size) |
| `m_closestField` | Field guide zoom factor (camera_width / closest_field) |

### Line Processing Mode

| Mode | Code | Output |
|------|------|--------|
| None | `lpNone (0)` | No processing, export as-is |
| Greyscale | `lpGrey (1)` | Greyscale colormap (ink = dark, paper = transparent) |
| Color | `lpColor (2)` | Full color colormap (HSV-based palette matching) |

### Auto-Adjust (greyscale mode only)

| Mode | Description |
|------|-------------|
| `AUTO_ADJ_NONE` | No adjustment |
| `AUTO_ADJ_BLACK_EQ` | Edge-based black equalization |
| `AUTO_ADJ_HISTOGRAM` | Cumulative histogram matching (first frame = reference) |
| `AUTO_ADJ_HISTO_L` | Line-width histogram matching |

### Line Processing Settings

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `m_sharpness` | 0-100 | 90 | Blur/detail balance (higher = sharper) |
| `m_despeckling` | 0-20 | 2 | Speckle removal threshold (pixel area) |
| `m_noAntialias` | Boolean | false | Disable standard antialiasing |
| `m_postAntialias` | Boolean | false | Enable MLAA (morphological AA) |
| `m_aaValue` | 0-100 | 70 | MLAA intensity |

---

## Step 3: Set Up Field Guide Registration

**Source:** `toonz/sources/include/toonz/cleanupparameters.h` (FDG_INFO)

The field guide system detects pegbar holes in scanned drawings for precise alignment:

### FDG_INFO Structure

```cpp
struct DOT {
    float x, y;           // Pegbar hole centroid (mm)
    int x1, y1, x2, y2;  // Bounding box (pixels)
    int area;             // Pixel count
    int lx, ly;           // Width/height (pixels)
};

struct FDG_INFO {
    string m_name;
    int ctr_type;                    // TRUE = center/angle/skew, FALSE = dot mode
    double ctr_x, ctr_y;            // Center position (mm)
    double ctr_angle;                // Rotation angle (degrees)
    double ctr_skew;                 // Skew angle (degrees)
    vector<DOT> dots;                // Detected pegbar holes
    double dist_ctr_to_ctr_hole;     // Center-to-hole distance
    double dist_ctr_hole_to_edge;    // Hole-to-edge distance
};
```

Field guide files (`.fdg`) are stored in `config/fdg/` and define the expected pegbar hole pattern.

---

## Step 4: Build the Cleanup Palette

**Source:** `toonz/sources/toonz/cleanupsettingspopup.cpp`

For color line processing (`lpColor`), the cleanup palette defines target colors:

### Palette Color Semantics

| Index | Role | Recognition Method |
|-------|------|-------------------|
| 0 | Paper (background) | Becomes transparent in output |
| 1 | Outline (ink) | Recognized by VALUE < threshold |
| 2+ | Match-lines | Recognized by HUE (with tolerance) |

### Per-Color Settings

| Parameter | Description |
|-----------|-------------|
| Brightness | -100 to 100, tonal shift |
| Contrast | 0 to 100, tonal range (0=flat, 100=normal) |
| Hue Range | 0-360 degrees, match tolerance |
| Saturation Threshold | 0-100%, minimum saturation for recognition |

---

## Step 5: Execute Cleanup Processing

**Source:** `toonz/sources/include/toonz/tcleanupper.h`

### TCleanupper (singleton engine)

```cpp
static TCleanupper *instance();
void setParameters(CleanupParameters *params);

CleanupPreprocessedImage *process(
    TRasterImageP &image,              // Input
    bool first_image,                  // First frame flag (for auto-adjust reference)
    TRasterImageP &onlyResampledImage, // Output: resampled intermediate
    bool isCameraTest,
    bool returnResampled,
    bool onlyForSwatch,
    TAffine *aff,                      // Output: computed transform
    TRasterP templateForResampled
);

TToonzImageP finalize(CleanupPreprocessedImage *src, bool isCleanupper);
```

### Processing Pipeline Order

```
INPUT: Full-color raster image
    |
    v
STEP 1: Resample & Geometric Transform
    - Calculate affine: scale -> rotate -> translate
    - Detect autocenter (pegbar holes)
    - Resample to output dimensions
    - Filter: ClosestPixel (same DPI) / Triangle (test) / Hann2 (normal)
    - Blur from sharpness: blur = max_blur^((100-sharpness)/(100-1))
    - Add white background (semitransparent pixels)
    |
    v
STEP 2: Auto-Adjust (greyscale only)
    - BLACK_EQ: Find darkest edges, remap black point
        1. Build 2D histogram: grey_level x edge_strength
        2. Find peak edge grey level
        3. Create LUT: remap so darkest -> user_black_value
    - HISTOGRAM: Match cumulative distribution to first-frame reference
        1. First frame: build reference cumulative histogram
        2. Subsequent: match cumulative distribution via LUT
    - HISTO_L: Match line-width distribution
        1. Analyze edge profiles per grey level
        2. Identify main line grey level
        3. Create LUT mapping current widths to reference widths
    |
    v
STEP 3: Color Preprocessing (RGB -> CM32 colormap)
    - Greyscale: Direct conversion to 8-bit tone
    - Color: HSV-based palette matching
        - Paper (color 0) -> transparent (tone 255)
        - Outline (color 1) -> recognized by VALUE threshold
        - Match-lines (2+) -> recognized by HUE only
        - Tone = pixel saturation or value (normalized)
        - Disputed pixels blended via PRODUCT
    |
    v
STEP 4: Post-Processing
    - Brightness/Contrast: Per-ink tone curve mapping
    - Despeckling: Remove isolated blots (0-20 pixel area)
    - MLAA: Morphological antialiasing (10 iterations, 0-100% intensity)
    - Convert CM32 -> RGB32 with palette
    |
    v
OUTPUT: TToonzImage (colormap + palette)
```

---

## Step 6: Save Cleanup Results

Cleaned frames are saved as ToonzRaster levels (`.tlv` format) with embedded palette. The cleanup settings can also be saved as `.cln` files for reuse.

### Commit Strategy

| Mode | What Changes | Speed |
|------|-------------|-------|
| INTERFACE | UI-only (path, rotation) | Instant |
| POSTPROCESS | Color/despeckling changes | Fast |
| FULLPROCESS | Resampling/autocenter/auto-adjust | Slow |

---

## Auto-Adjust Algorithms Detail

### BLACK_EQ (Edge-Based Black Equalization)

```
1. Build 2D histogram: grey_level x edge_strength
   - Compute 4-directional edge gradients at each pixel
   - Take maximum gradient as edge strength
2. Find peak edge grey level (max average edge per grey)
3. Find darkest pixels within peak region
4. Create LUT: remap pixels so darkest -> reference black
   LUT[g] = 255 - (255-g) * (255-Black)/(255-darkest)
5. Apply LUT to image
```

### HISTOGRAM (Global Cumulative Matching)

```
1. First frame: build reference cumulative distribution
2. Each subsequent frame:
   - Build current cumulative distribution
   - Create LUT matching current to reference
   - Apply LUT
```

### HISTO_L (Line-Width Distribution)

```
1. For each grey level, measure line widths at edges
2. Build histogram of widths per grey level
3. Match line-width distribution to reference
4. Create LUT preserving relative distributions
```

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Parameters | `cleanupparameters.h` | All cleanup settings |
| Engine | `tcleanupper.h` | Core cleanup pipeline |
| Settings UI | `cleanupsettingspopup.cpp` | UI configuration |
| Cleanup UI | `cleanuppopup.cpp` | Execution dialog |
| Scanner | `scanpopup.cpp` | TWAIN scanner integration |
| Auto-Adjust | `autoadjust.cpp` | Tonal normalization algorithms |
| Field Guide | FDG_INFO in `cleanupparameters.h` | Registration data |

---

## Headless API Gaps

The current headless API has **no cleanup functionality**. Everything needed:

1. **Image loading** -- load scanned raster images (partially available via `Image.load()`)
2. **Cleanup parameters** -- expose CleanupParameters as a scriptable object
3. **Field guide** -- load FDG files, configure registration
4. **Auto-center** -- detect pegbar holes, compute alignment
5. **Auto-adjust** -- BLACK_EQ, HISTOGRAM, HISTO_L tonal normalization
6. **Line processing** -- greyscale/color mode, sharpness, despeckling
7. **Color matching** -- palette-based HSV recognition
8. **MLAA** -- morphological antialiasing
9. **Batch processing** -- process multiple frames with first-frame reference
10. **Output** -- save as TLV with embedded palette
