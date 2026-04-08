# OpenToonz Lip Sync Workflow

Extracted from the OpenToonz source code -- a pipeline for synchronizing mouth animation to dialogue audio.

---

## Overview

OpenToonz supports three lip sync approaches: **manual** (text file mapping phonemes to frames), **automatic** (Rhubarb speech-to-phoneme analysis), and **Magpie import** (legacy third-party format). All methods produce the same output: XSheet cells populated with mouth shape drawings matched to phonemes.

---

## Step 1: Prepare Mouth Shape Drawings

Create a level with one drawing per phoneme. OpenToonz uses the **Preston Blair phoneme set** (10 shapes):

| Code | Phoneme | Mouth Shape |
|------|---------|-------------|
| AI | ah, ay | Wide open mouth |
| E | ee | Wide smile |
| O | oh | Round open |
| U | oo | Small round |
| L | el, ul | Tongue tip visible |
| WQ | w, q | Pursed lips |
| MBP | m, b, p | Closed lips |
| FV | f, v | Lower lip under teeth |
| Other/Etc | misc consonants | Slightly open |
| Rest | silence | Neutral/closed |

Each phoneme maps to a frame ID in the mouth shapes level.

---

## Step 2: Choose Lip Sync Method

### Method A: Manual (Text File)

**Source:** `toonz/sources/toonz/lipsyncpopup.cpp`

**File format:** Plain text with alternating frame/phoneme pairs:
```
1 ai
5 mbp
8 e
12 rest
```

**Process:**
1. Load lip sync data file (TXT/DAT)
2. Validate format (space-separated frame/phoneme pairs)
3. Select mouth drawing from level for each of the 10 phonemes
4. Set start frame for insertion
5. Apply: for each frame range, assign corresponding mouth drawing to XSheet cells
6. Optionally extend rest drawing to end marker

### Method B: Automatic (Rhubarb)

**Source:** `toonz/sources/toonz/autolipsyncpopup.cpp`

Integrates the **Rhubarb Lip Sync** tool (external binary) for automatic speech-to-phoneme analysis.

**Process:**
1. Check Rhubarb availability (path from Preferences)
2. Select audio source: sound column in XSheet or external WAV/AIFF file
3. Optionally provide dialogue script text for improved accuracy
4. Configure start frame
5. Execute Rhubarb:
   ```
   rhubarb -o temp.dat -f dat --datUsePrestonBlair
           [--datFrameRate fps] [--script script.txt] audio.wav
   ```
6. Monitor progress asynchronously (QProcess)
7. Parse DAT output (same format as manual: frame/phoneme pairs)
8. Apply mapping to XSheet cells

**Timeout:** 10 minutes default.

### Method C: Magpie Import

**Source:** `toonz/sources/toonz/magpiefileimportpopup.cpp`

Imports legacy **Toonz Magpie** lip sync files.

**File format:** Pipe-delimited:
```
Toonz
1|ai|dialogue text
5|mbp|
8|e|more text
```

**Process:**
1. Parse Magpie file (header "Toonz", then `frame|phoneme|comment` lines)
2. Display phoneme frames, allow frame selection per phoneme
3. Preview with FlipBook viewer
4. Apply to XSheet

---

## Step 3: Apply to XSheet

All three methods produce the same result:

1. Create undo block (for rollback)
2. For each phoneme range in the data:
   - Look up the mouth drawing frame ID for this phoneme code
   - Set XSheet cells in the target column from range start to range end
3. Optionally extend the rest drawing beyond the last phoneme

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Manual Lip Sync | `lipsyncpopup.cpp` | Text file import + manual mapping |
| Auto Lip Sync | `autolipsyncpopup.cpp` | Rhubarb integration |
| Magpie Import | `magpiefileimportpopup.cpp` | Legacy format import |

---

## Headless API Gaps

1. **Phoneme data parsing** -- load TXT/DAT lip sync files
2. **XSheet cell batch assignment** -- assign mouth drawings across frame ranges
3. **Audio analysis** -- Rhubarb integration (or expose as external tool call)
4. **Mouth shape level management** -- create/select phoneme drawings
