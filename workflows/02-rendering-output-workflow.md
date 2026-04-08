# OpenToonz Rendering/Output Workflow

Extracted from the OpenToonz source code -- a step-by-step pipeline for rendering scenes to final deliverable files.

---

## Overview

OpenToonz has a multi-tier rendering system: **TRenderer** (low-level multithreaded engine) feeds into **MovieRenderer** (high-level orchestrator) which writes frames via **LevelUpdater** (format-aware file writer). The system supports image sequences, video files, stereo 3D, and multi-layer separation.

---

## Step 1: Configure Output Properties

**Source:** `toonz/sources/include/toonz/toutputproperties.h`

The `TOutputProperties` class stores all output settings for a scene:

| Property | Type | Description |
|----------|------|-------------|
| `m_path` | TFilePath | Output file path |
| `m_frameRate` | double | Output FPS |
| `m_from, m_to, m_step` | int | Frame range and step |
| `m_offset` | int | Frame numbering offset |
| `m_whichLevels` | int | AllLevels / SelectedOnly / AnimatedOnly |
| `m_multimediaRendering` | int | 0=None, 1=Columns, 2=Layers |
| `m_maxTileSizeIndex` | int | 0=off, 1=large, 2=medium, 3=small |
| `m_threadIndex` | int | 0=single, 1=half CPUs, 2=all CPUs |
| `m_subcameraPreview` | bool | Sub-camera render mode |

---

## Step 2: Configure Render Quality

**Source:** `toonz/sources/include/trasterfx.h`

### TRenderSettings

```cpp
struct TRenderSettings {
    TAffine m_affine;                  // Output transform
    double m_gamma;                    // Post-render gamma correction
    int m_bpp;                         // Bits per pixel: 32, 64, or float
    int m_maxTileSize;                 // Max tile size in MB
    ResampleQuality m_quality;         // Filter mode (17 options)
    FieldPrevalence m_fieldPrevalence; // Interlacing
    bool m_linearColorSpace;           // Render in linear light
    double m_colorSpaceGamma;          // Working color space gamma
    bool m_stereoscopic;               // 3D dual-output mode
    double m_stereoscopicShift;        // Camera separation (inches)
    TRectD m_cameraBox;                // Camera bounds
};
```

### Resample Quality Modes (17 filters)

| Filter | Use Case |
|--------|----------|
| StandardResampleQuality | Triangle filter (default) |
| ImprovedResampleQuality | Hann2 filter |
| HighResampleQuality | Hamming3 filter |
| Mitchell_FilterResampleQuality | Good for scaling up |
| Lanczos2/3_FilterResampleQuality | Highest quality downscale |
| ClosestPixel_FilterResampleQuality | Pixel art (no interpolation) |
| Bilinear_FilterResampleQuality | Fast, decent quality |

### Channel Depth

| BPP | Precision | Use Case |
|-----|-----------|----------|
| 32 | 8-bit per channel | Standard output (PNG, TGA, MP4) |
| 64 | 16-bit per channel | High dynamic range (TIFF, EXR) |
| float | 32-bit float | Maximum precision (EXR, compositing) |

---

## Step 3: Choose Output Format

**Source:** `toonz/sources/toonz/formatsettingspopups.cpp`, `toonz/sources/include/tiio.h`

### Supported Formats

**Image Sequences:**
- TGA, PNG, TIFF, JPG, BMP, DPX, EXR
- Each frame is a separate numbered file
- Supports alpha channel (except JPG)

**Video Files:**
- MOV, MP4, AVI (platform-dependent), WebM
- Encoded via FFmpeg or system codecs
- Single file containing all frames + audio

**Toonz Levels:**
- TLV (Toonz Raster Level)
- PLI (Toonz Vector Level)

### Format-Specific Settings

Each format has a `TPropertyGroup` with codec-specific options:
- **PNG:** Compression level
- **TIFF:** Compression (None, LZW, ZIP, JPEG), bits per sample
- **JPG:** Quality (0-100)
- **EXR:** Compression (None, RLE, ZIP, PIZ, PXR24, B44, DWAA), linear color space flag
- **MP4/MOV:** Codec (H.264, H.265, ProRes), bitrate, CRF quality

---

## Step 4: Set Up the MovieRenderer

**Source:** `toonz/sources/include/toonz/movierenderer.h`

```cpp
MovieRenderer(ToonzScene *scene, const TFilePath &moviePath,
              int threadCount, bool cacheResults);
```

### Setup Flow

1. `setRenderSettings(settings)` -- quality, color space, gamma
2. `setDpi(xDpi, yDpi)` -- output DPI
3. `addFrame(frame, fxPair)` -- queue each frame with its FX tree root
4. `addListener(listener)` -- register callbacks for progress/completion

### Listener Callbacks

```cpp
class Listener {
    virtual void onSequenceCompleted(const TFilePath &path);
    virtual void onFrameCompleted(int frame);
    virtual void onFrameFailed(int frame, TException &e);
    virtual void onStatusChanged(const std::string &status);
};
```

---

## Step 5: Execute the Render

**Source:** `toonz/sources/include/trenderer.h`

### TRenderer (low-level engine)

```cpp
TRenderer(int nThread);
unsigned long startRendering(const vector<RenderData> *data);
void abortRendering(unsigned long renderId);
void enablePrecomputing(bool on);
```

### Complete Render Flow

```
MovieRenderer.start()
    |
    v
prepareForStart()
    - Creates LevelUpdater (handles file format)
    - Sets frame rate in file header
    - Builds RenderData vector
    |
    v
TRenderer.startRendering(renderDatas)
    - Spawns N worker threads
    - Distributes frames to threads
    |
    v
[Each thread]
    1. dryCompute() -- predictive cache analysis
    2. TRasterFx.compute() -- actual render (recursive FX tree)
    3. onRenderRasterCompleted() callback
        |
        v
    postProcessImage()
        - Gamma correction (once per frame cluster)
        - Color space conversion (linear -> sRGB)
        - BPP conversion (64-bit -> 32-bit if needed)
        - Watermark/scene numbering overlay
        |
        v
    LevelUpdater.update(fid, image)
        - Writes frame to disk in chosen format
    |
    v
onSequenceCompleted()
    - LevelUpdater.close() -- finalize file
    - Audio track embedding (for video formats)
```

---

## Step 6: Tile Granularity & Memory Management

**Source:** `toonz/sources/include/tfxcachemanager.h`

### Tile Sizes

| Setting | Max Tile MB | Use Case |
|---------|------------|----------|
| Off | Unlimited | Simple scenes, plenty of RAM |
| Large | 50 MB | General use |
| Medium | 10 MB | Complex FX chains |
| Small | 2 MB | Memory-constrained systems |

### Predictive Caching

Before actual rendering, `dryCompute()` traverses the FX tree to:
- Predict memory requirements per tile
- Pre-allocate buffers
- Subdivide large tiles if needed
- Improve cache hit rates

### Frame Clustering

Identical frames (e.g., held drawings) are detected and rendered once, then the raster is reused for all duplicate frames.

---

## Step 7: Multi-Layer Rendering

**Source:** `toonz/sources/include/toonz/multimediarenderer.h`

`MultimediaRenderer` renders each layer to a separate file:

| Mode | Output | Description |
|------|--------|-------------|
| None (0) | Single composite | Standard rendering |
| Columns (1) | One file per column | `output_columnName.ext` |
| Layers (2) | One file per FX terminal | `output_layerName.ext` |

Each layer gets its own MovieRenderer instance sharing a common TRenderer.

---

## Step 8: Stereoscopic 3D Rendering

**Source:** `movierenderer.cpp`

When `m_stereoscopic = true`:
1. Scene is rendered twice with shifted cameras
2. Left eye: camera offset by `-stereoscopicShift/2`
3. Right eye: camera offset by `+stereoscopicShift/2`
4. Output files: `filename_l.ext` and `filename_r.ext`
5. Audio is shared between both outputs
6. Preview combines via `TRop::makeStereoRaster`

---

## Step 9: Audio Integration

**Source:** `movierenderer.cpp`

For video output formats:
1. Extract audio from XSheet sound columns (`makeSound()`)
2. Trim to frame range
3. Insert silence for clapperboard duration (if enabled)
4. Embed in output file via `saveSoundTrack()`

---

## Step 10: Interlaced Field Rendering

For broadcast output:
- **NoField** -- Progressive (standard)
- **EvenField** -- PAL (25 fps, even lines first)
- **OddField** -- NTSC (29.97 fps, odd lines first)

Each frame is rendered as two half-resolution fields, interleaved in the output.

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| MovieRenderer | `movierenderer.h` | High-level render orchestration |
| MultimediaRenderer | `multimediarenderer.h` | Per-layer output |
| TRenderer | `trenderer.h` | Low-level multithreaded engine |
| TRenderSettings | `trasterfx.h` | Quality/color/gamma config |
| TOutputProperties | `toutputproperties.h` | Scene output settings |
| OutputSettingsPopup | `outputsettingspopup.cpp` | UI for all output options |
| FormatSettings | `formatsettingspopups.cpp` | Format-specific codec settings |
| LevelUpdater | `levelupdater.h` | Frame-level file writing |
| Tiio | `tiio.h` | Format reader/writer registry |
| FX Cache | `tfxcachemanager.h` | Intermediate result caching |

---

## Headless API Gaps

The current headless API has `Renderer` class with `renderFrame(scene, frame)` and `renderScene(scene)` but is limited to:
- PNG output only (via `image.save()`)
- No format/codec selection
- No render quality settings (resample filter, channel depth)
- No frame range control
- No video output (MP4/MOV)
- No multi-layer rendering
- No stereoscopic output
- No audio embedding
- No threading control
- No tile granularity settings
- No progress callbacks

### Needed for Full Rendering

1. **Format selection** -- specify output format and codec
2. **Quality settings** -- resample filter, BPP, color space, gamma
3. **Frame range** -- from/to/step with numbering offset
4. **Video output** -- MP4/MOV with audio embedding
5. **Multi-layer export** -- per-column or per-terminal output
6. **Threading** -- control number of render threads
7. **Tile granularity** -- memory management for complex scenes
8. **Progress reporting** -- frame completion callbacks
