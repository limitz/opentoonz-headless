# OpenToonz Compositing/FX Workflow

Extracted from the OpenToonz source code -- a step-by-step pipeline for layering animated elements with effects.

---

## Overview

OpenToonz uses a **Directed Acyclic Graph (FxDag)** to manage all visual effects. Each column in the XSheet has an implicit FX node (TLevelColumnFx). Effects are inserted between columns and the output node, forming chains that are traversed depth-first during rendering.

---

## Step 1: Understand the FX Graph Architecture

**Source:** `toonz/sources/include/toonz/fxdag.h`

The FxDag contains:
- **Internal FX set** (`m_internalFxs`) -- all effect nodes
- **Terminal FX set** (`m_terminalFxs`) -- effects connected to the xsheet output
- **XSheet FX** (`m_xsheetFx`) -- virtual node representing the xsheet itself
- **Output FX** (`m_outputFxs`) -- final render endpoints (can have multiple)

Key methods:
- `assignUniqueId(fx)` -- ensures unique IDs
- `checkLoop(inputFx, fx)` -- validates no cycles
- `addToXsheet(fx)` / `removeFromXsheet(fx)` -- terminal node management
- `getFxById(id)` -- lookup by identifier

---

## Step 2: Understand the Port System

**Source:** `toonz/sources/include/tfx.h`

Every effect has **input ports** and **output connections**:

```
TFxPort (abstract base)
  -> TRasterFxPort (typed port for raster effects)
```

- `addInputPort(name, port)` -- register a static input
- `addInputPort(name, port, groupIndex)` -- dynamic port group
- `getInputPort(index)` / `getInputPort(name)` -- retrieve
- `addOutputConnection(port)` -- called when another FX connects to this one

### Dynamic Port Groups

For effects with variable input counts (e.g., multi-layer blends):

```cpp
class TFxPortDynamicGroup {
    int minPortsCount();       // minimum ports always visible
    string portsPrefix();      // naming convention: "foreground_0", "foreground_1", ...
};
```

---

## Step 3: Create and Configure Effects

**Source:** `toonz/sources/toonz/insertfxpopup.cpp`, `toonz/sources/stdfx/`

### Effect Creation

```cpp
TFx *fx = TFx::create("STD_blurFx");  // Standard prefix: STD_
```

### Three Insertion Modes

| Mode | Pattern | Use Case |
|------|---------|----------|
| **Add** | `selectedFx -> newFx -> previousOutput` | Append to chain |
| **Insert** | `upstream -> newFx -> selectedFx` | Splice between |
| **Replace** | Remove old, wire new in its place | Swap effect |

### Effect Categories (~200 total)

**Color/Tone Adjustments (30+):**
- `STD_brightContFx` -- brightness/contrast
- `STD_adjustLevelsFx` -- levels/curves per channel
- `STD_hsvScaleFx` -- hue/saturation/value
- `STD_toneCurveFx` -- curve-based tone
- `STD_posterizeFx` -- color quantization
- `STD_changeColorFx` -- color shift

**Blur Effects (15+):**
- `STD_blurFx` -- Gaussian blur
- `STD_directionalBlurFx` -- motion blur (angle + distance)
- `STD_radialBlurFx` -- zoom blur
- `STD_rotationalBlurFx` -- spin blur
- `STD_localBlurFx` -- selective/masked blur

**Distortion/Transformation (20+):**
- `STD_freeDistortFx` -- corner-pin warp
- `STD_warpFx` -- mesh deformation
- `STD_rippleFx`, `STD_linearWaveFx`, `STD_randomWaveFx` -- wave patterns
- `STD_cornerPinFx` -- perspective pinning

**Light/Glow (15+):**
- `STD_glowFx` -- bloom/aura
- `STD_backlitFx` -- backlit glow
- `STD_bodyHighlightFx` -- cel shading highlights
- `STD_rayLitFx` -- radial light rays
- `STD_targetSpotFx` -- spotlight

**Procedural/Noise (20+):**
- `STD_particlesFx` -- particle systems (73 params)
- `STD_noiseFx` -- noise generator
- `STD_cloudsFx` -- cloud generation
- `STD_perlinNoiseFx` -- Perlin noise

**Gradients/Generators (10+):**
- `STD_radialGradientFx` -- radial gradient
- `STD_diamondGradientFx`, `STD_squareGradientFx`
- `STD_colorCardFx` -- solid color
- `STD_iwaTimeCodeFx` -- timecode overlay
- `STD_iwaTextFx` -- text overlay

**Blend/Composite (50+):**
All inherit `TBlendForeBackRasterFx` with two input ports (`m_up`, `m_down`):
- `ino_blend_over` -- Porter-Duff over (standard)
- `ino_blend_add` -- linear add
- `ino_blend_multiply` -- multiply
- `ino_blend_screen` -- screen
- `ino_blend_overlay`, `ino_blend_soft_light`, `ino_blend_hard_light`
- `ino_blend_darken`, `ino_blend_lighten`
- `ino_blend_color_burn`, `ino_blend_color_dodge`
- `ino_blend_cross_dissolve`, `ino_blend_dissolve`

---

## Step 4: Connect Effects into Chains

**Source:** `toonz/sources/include/toonz/scenefx.h`

### Single-Input Filter Pattern

Most effects take one input and produce one output:

```
Column 0 (TLevelColumnFx)
    -> BlurFx
        -> GlowFx
            -> XSheet Output
```

### Two-Input Blend Pattern

Blend effects combine two sources:

```
Column 0 (Background) -> m_down
                                -> OverFx -> Output
Column 1 (Foreground) -> m_up
```

### Multi-Layer Composition

The standard scene compositing stacks columns back-to-front using Over:

```
Col 0 (background)
  Over -> Col 1 (midground)
    Over -> Col 2 (foreground)
      -> Output
```

### Zerary Effects (Generators)

Zero-input effects that generate content:
- Placed in their own column (TZeraryColumnFx)
- No upstream connection needed
- Examples: CloudsFx, GradientFx, NoiseFx

---

## Step 5: Configure Effect Parameters

**Source:** Individual effect source files in `toonz/sources/stdfx/`

Each effect exposes parameters via `TParamContainer`:

| Param Type | Example | Value Format |
|------------|---------|--------------|
| `TDoubleParamP` | Blur radius | Single number |
| `TIntParamP` | Posterize levels | Integer |
| `TBoolParamP` | Enable flag | Boolean |
| `TIntEnumParamP` | Blend mode | Integer index |
| `TPointParamP` | Center point | (x, y) |
| `TPixelParamP` | Color | (r, g, b, a) |
| `TRangeParamP` | Lifetime | (min, max) |
| `TStringParamP` | Text | String |

All `TDoubleParamP` and `TPointParamP` parameters are **keyframeable** -- values can change per frame.

---

## Step 6: Render the FX Tree

**Source:** `toonz/sources/include/toonz/scenefx.h`, `toonz/sources/include/trasterfx.h`

### Render Tree Building

For each frame, `buildSceneFx()` creates a temporary render tree:

```
buildSceneFx(scene, frame, xsheet, root, transforms, isPreview, whichLevels, shrink)
```

Transform flags:
- `BSFX_CAMERA_TR` -- apply camera transform
- `BSFX_CAMERA_DPI_TR` -- apply camera DPI scaling
- `BSFX_COLUMN_TR` -- apply column transforms (pegbar affines)
- `BSFX_DEFAULT_TR` -- all of above

### Render Execution Flow

```
OutputFx.compute(tile, frame, renderSettings)
    |
    v
canHandle(affine)? -> Split affine into handled + unhandled
    |
    v
doCompute(tile, frame, settings)  [PURE VIRTUAL]
    |
    v
For each input port:
    inputFx.compute(inputTile, frame, inputSettings)  [recursive DFS]
    |
    v
Process input data -> Write to output tile
    |
    v
applyAffine() for unhandled affine portion [resampling]
```

### TRenderSettings

```cpp
struct TRenderSettings {
    TAffine m_affine;               // Transform after FX
    double m_gamma;                 // Output gamma
    int m_bpp;                      // 32, 64, or float
    int m_maxTileSize;              // Max tile MB
    ResampleQuality m_quality;      // 17 filter modes
    FieldPrevalence m_fieldPrevalence;  // Interlacing
    bool m_linearColorSpace;        // Linear gamma (2.2)
    TRectD m_cameraBox;             // Camera bounds
};
```

---

## Step 7: Advanced -- Macro FX

**Source:** `toonz/sources/include/toonz/txsheetexpr.h`

Macro FX bundle multiple effects into a single compound node:
- `TMacroFx` contains a list of internal FX with their own connections
- Exposes selected input ports to the outside
- Save/load as a single reusable preset

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| FX DAG | `fxdag.h` | Graph structure |
| Base FX | `tfx.h` | Abstract base, ports, params |
| Raster FX | `trasterfx.h` | Renderable base, TRenderSettings |
| Column FX | `tcolumnfx.h` | Per-column FX wrappers |
| Scene FX | `scenefx.h` | Render tree builder |
| FX Commands | `fxcommand.h` | Add/Insert/Replace operations |
| Insert FX | `insertfxpopup.cpp` | Effect browser and insertion UI |
| Blend Base | stdfx `TBlendForeBackRasterFx` | Two-input blend base class |
| Standard FX | `toonz/sources/stdfx/` | 200+ effect implementations |

---

## Headless API Gaps

The current headless API has `Effect` class with `scene.connectEffect(colIdx, effect)` but is limited to:
- Single-effect chains only (no A->B->C)
- No multi-input effects (blends)
- No FxDag graph construction
- No per-column FX management
- No effect presets
- No zerary (generator) effects in columns
- No macro/compound effects

### Needed for Full Compositing

1. **Effect chaining** -- connect output of one effect to input of another
2. **Multi-input blends** -- connect two columns to a blend effect
3. **FxDag access** -- add/remove/query effects in the graph
4. **Terminal management** -- control which effects connect to output
5. **Zerary columns** -- create generator-only columns
6. **Effect presets** -- save/load parameter configurations
7. **Per-frame parameter animation** -- already partially supported via `setParamKeyframe`
