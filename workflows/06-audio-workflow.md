# OpenToonz Audio/Sound Workflow

Extracted from the OpenToonz source code -- a pipeline for managing audio tracks synchronized with animation.

---

## Overview

OpenToonz manages audio via **sound columns** in the XSheet. Each sound column holds one or more `ColumnLevel` entries (audio clips with offset/duration). Audio is used for timing reference during animation, lip sync, and embedded in final video output.

---

## Step 1: Import or Record Audio

### Import Audio File

Supported formats: WAV, AIFF, MP3 (via system decoders).

Sound files are loaded as `TXshSoundLevel` objects and placed in XSheet sound columns.

### Record Audio

**Source:** `toonz/sources/toonz/audiorecordingpopup.cpp`

| Setting | Options | Default |
|---------|---------|---------|
| Input device | Auto-detected | System default |
| Sample rate | 8000, 11025, 22050, 44100, 48000, 96000, 192000 Hz | 44100 (CD) |
| Format | Mono/Stereo, 8/16/24/32-bit | Mono 16-bit |
| Sync playback | Boolean | false |

Recording outputs a WAV file to cache, then creates a new sound column.

---

## Step 2: Place Audio in XSheet

**Source:** `toonz/sources/include/toonz/txshsoundcolumn.h`

### TXshSoundColumn

| Property | Type | Description |
|----------|------|-------------|
| `m_levels` | QList<ColumnLevel*> | Sound clips in this column |
| `m_volume` | double (0.0-1.0) | Column volume |
| `m_player` | TSoundOutputDevice* | Playback device |

### ColumnLevel (individual clip)

| Property | Type | Description |
|----------|------|-------------|
| `m_soundLevel` | TXshSoundLevel* | Audio data reference |
| `m_startFrame` | int | XSheet row where clip starts |
| `m_startOffset` | int | Frames trimmed from start |
| `m_endOffset` | int | Frames trimmed from end |
| `m_fps` | double | Frame rate for sample-to-frame conversion |

---

## Step 3: Synchronize with Animation

### Playback

- `play(soundTrack, startFrame, endFrame, loop)` -- play audio range
- `stop()` -- stop playback
- Scrub mode: frame-by-frame audio preview

### Waveform Display

`TXshSoundLevel` provides sample-to-pixel mapping for waveform visualization in the XSheet timeline:
- `getValueAtPixel(pixel)` -- returns amplitude at position
- `computeValues()` -- precomputes display values
- `setFrameRate(fps)` -- updates time mapping

---

## Step 4: Render with Audio

Audio from sound columns is mixed and embedded in video output:
1. `getOverallSoundTrack()` -- mix all sound levels in range
2. Trim to output frame range
3. Insert silence for clapperboard (if enabled)
4. Embed via `LevelWriter.saveSoundTrack()`

---

## Key Source Files

| System | File | Purpose |
|--------|------|---------|
| Sound Level | `txshsoundlevel.h` | Audio data + waveform |
| Sound Column | `txshsoundcolumn.h` | XSheet audio timeline |
| Recording | `audiorecordingpopup.cpp` | Live audio capture |
| Playback | TSoundOutputDevice (platform) | Audio output |

---

## Headless API Gaps

1. **Sound column creation** -- add sound columns to XSheet
2. **Audio import** -- load WAV/AIFF into sound levels
3. **Clip placement** -- set start frame, offset, duration
4. **Volume control** -- per-column volume
5. **Audio mixing** -- combine multiple sound columns
6. **Render integration** -- embed audio in video output
