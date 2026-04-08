# OpenToonz Format Conversion Workflow

Extracted from the OpenToonz source code -- a pipeline for batch-converting between level formats.

---

## Overview

The converter transforms levels between raster formats (TGA, PNG, TIFF, etc.) and Toonz-native formats (TLV). It handles DPI adjustment, background color blending, palette generation, and special TLV conversion modes for painted artwork.

---

## Step 1: Select Source and Target Format

**Source:** `toonz/sources/toonz/convertpopup.cpp`

### Supported Output Formats

- **Image sequences:** TGA, PNG, JPG, BMP, TIFF
- **Toonz raster:** TLV (Toonz Level, indexed colormap)

### TLV Conversion Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| Unpainted | Outline only, no fill colors | Clean line art |
| Painted from Non-AA | Full-color non-antialiased source (Retas-style) | Painted cel art |
| Painted from two images | Ink layer + paint layer combined | Separated ink/paint |

---

## Step 2: Configure Conversion Options

| Option | Type | Description |
|--------|------|-------------|
| Background Color | RGBA | Fill color for transparent areas |
| Skip Existing | Boolean | Don't overwrite existing files |
| Remove Dot | Boolean | Remove dot before frame number in filenames |
| Frame Range | From/To | Subset of frames to convert |

### TLV-Specific Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| DPI Mode | Enum | Image DPI | Image DPI / Camera DPI / Custom |
| Custom DPI | Double | 72 | Used when DPI Mode = Custom |
| Append Default Palette | Boolean | true | Add standard palette |
| Remove Unused Styles | Boolean | false | Clean up palette |
| Save Backup | Boolean | false | Copy to nopaint folder |
| Antialiasing | Double | varies | AA intensity for NAA conversion |
| Output Palette Path | FilePath | -- | Use specific palette file |

---

## Step 3: Execute Conversion

### Processing Flow

```
For each source level:
    |
    v
1. Detect source format (TLV, raster, etc.)
2. Determine destination path (same name, new extension)
3. Check existing file behavior (skip/overwrite)
    |
    v
4a. To TLV (Painted from Non-AA):
    - ImageUtils::convertNaa2Tlv()
    - Palette merging with reference palette
    |
4b. To TLV (Other):
    - Convert2Tlv class (frame-by-frame)
    - DPI adjustment
    - Palette generation
    |
4c. Full-Color format:
    - ImageUtils::convert()
    - Background color blending
    - Format-specific encoding
    |
    v
5. Write output file
6. Optional: nopaint backup copy
7. Update icon cache
```

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Convert UI | `convertpopup.cpp` | Dialog and batch orchestration |
| Binarize | `binarizepopup.cpp` | B&W conversion specifically |
| Convert2Tlv | Internal class | Raster-to-TLV conversion engine |
| ImageUtils | `imageutils.h` | convertNaa2Tlv and helpers |

---

## Headless API Gaps

1. **Level format conversion** -- convert between formats programmatically
2. **DPI adjustment** -- set output DPI mode and value
3. **TLV conversion** -- raster-to-colormap with palette
4. **Background color** -- composite over solid background
5. **Batch processing** -- convert multiple levels/frames
6. **Palette management** -- append, merge, remove unused styles
