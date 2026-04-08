# OpenToonz Export/Interchange Workflow

Extracted from the OpenToonz source code -- pipelines for exporting scene data and importing external formats.

---

## Overview

OpenToonz supports exporting complete scenes (with all assets), camera track data, and XSheet PDFs. It also imports XDTS/SXF files (multi-layer image sequences from DCP/EDL tools). These workflows enable interoperability with external animation and compositing tools.

---

## Export Scene (Portable Package)

**Source:** `toonz/sources/toonz/exportscenepopup.cpp`

### Process

1. Select destination folder
2. Scene resource collector traverses XSheet
3. Gathers all assets: palettes, levels, plugins, references
4. Copies files maintaining folder structure
5. Creates portable TNZ with relative paths
6. Verifies collection completeness

### Output

A self-contained folder with the TNZ scene file and all referenced levels, palettes, and resources.

---

## XDTS/SXF Import (Multi-Layer Sequences)

**Source:** `toonz/sources/toonz/xdtsimportpopup.cpp`

### Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| Level Mapping | File paths | Auto-detect | Map level names to image sequences |
| Cell Mark Tick1 | Int | 6 | Mark for start/key frames |
| Cell Mark Tick2 | Int | 8 | Mark for reference frames |
| Image Rename | Boolean | true | Remove numerical padding |
| Conversion Mode | Enum | None | None / Settings popup / NAA unpainted |
| DPI Mode | Enum | Image DPI | Image / Camera / Custom (120 default) |
| Append Palette | Boolean | true | Add default palette |

### Process

1. Parse XDTS file metadata, extract level names
2. Auto-detect image sequence files in same directory
3. User assigns each level to filesystem path
4. Apply cell marks to frame range
5. Optionally convert formats (NAA->TLV with DPI/palette)
6. Insert converted levels into XSheet with mark assignments

---

## Camera Track Export

**Source:** `toonz/sources/toonz/exportcameratrackpopup.cpp`

Exports camera transform keyframes for use in external compositing tools (After Effects, Nuke, etc.).

---

## XSheet PDF Export

**Source:** `toonz/sources/toonz/exportxsheetpdf.cpp`

Exports the XSheet timing chart as a printable PDF for traditional animation paper timing reference.

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Scene Export | `exportscenepopup.cpp` | Portable scene packaging |
| XDTS Import | `xdtsimportpopup.cpp` | Multi-layer sequence import |
| Camera Export | `exportcameratrackpopup.cpp` | Camera keyframe export |
| PDF Export | `exportxsheetpdf.cpp` | XSheet timing chart PDF |

---

## Headless API Gaps

1. **Scene export** -- package scene with all assets
2. **XDTS import** -- parse and load multi-layer sequences
3. **Camera track export** -- export transform data
4. **XSheet PDF** -- generate timing chart
