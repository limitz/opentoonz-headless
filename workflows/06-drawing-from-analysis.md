# Workflow 06: Drawing From Analysis

Lessons learned from analyzing reference artwork and attempting to reproduce/synthesize drawings through the headless API.

## Stroke Representation

### TStroke Bezier Control Points

TStroke uses quadratic Bezier splines. Points at **even indices** are on-curve, **odd indices** are off-curve control handles. When passing a series of intended positions as control points, the odd-indexed points pull the curve away from the intended path, causing wild overshoots.

**Fix:** Insert midpoints between every pair of intended positions. This puts every intended point on an even (on-curve) index:

```python
def smooth_pts(pts):
    result = []
    for i in range(len(pts)):
        result.append(pts[i])
        if i < len(pts) - 1:
            result.append(((pts[i][0]+pts[i+1][0])/2, (pts[i][1]+pts[i+1][1])/2))
    return result
```

For strokes with per-point thickness, interpolate thickness at midpoints too:

```python
def smooth_pts_thick(pts):
    # pts are (x, y, thickness) tuples
    result = []
    for i in range(len(pts)):
        result.append(pts[i])
        if i < len(pts) - 1:
            result.append(((pts[i][0]+pts[i+1][0])/2,
                          (pts[i][1]+pts[i+1][1])/2,
                          (pts[i][2]+pts[i+1][2])/2))
    return result
```

## How to Draw Characters

### Don't Assemble Parts

Wrong: draw a circle head, a bean torso, stick arms, stick legs as separate shapes and place them together. This produces segmented, mechanical figures.

### Don't Use Centerlines

Wrong: draw single-line strokes with thickness variation to suggest volume. This produces stick figures, even with variable thickness. The thickness values in stage coordinates are too small to create real volume.

### Draw Contour Outlines

Right: draw the **silhouette edges** of 3D forms. A character is made of volumes (sphere head, cylinder limbs, bean torso). Each volume has a left edge and a right edge. Draw those edges as separate contour strokes.

The **right body contour** is one flowing line: foot → ankle → shin → knee → thigh → hip → waist → ribs → shoulder → neck → jaw → head → crown.

The **left body contour** mirrors it on the other side.

The space *between* the two contour lines is the body's volume.

### Shoulders Have Volume

The arm doesn't start at the same point as the body contour. The shoulder is a rounded bump in the body contour:

- **Body contour** goes: chest → shoulder bulge OUT → rounds back IN → neck
- **Arm outer edge** starts from the shoulder peak (the outermost point of the bulge)
- **Arm inner edge** returns to the armpit (lower, tucked against the body)

This creates a real rounded shoulder joint where the arm emerges from a 3D form.

### Contours Flow Continuously

In gesture drawing, contour lines flow from one body part into the next without breaks. The right edge of the torso curves up and becomes the right edge of the neck and then the right edge of the head. One continuous stroke.

## Shading With Hatching

### Not Broad Strokes

Wrong: use a single wide stroke down the center of a form to suggest volume. This just makes a fat line.

### Parallel Curved Hatching

Right: fill forms with multiple parallel strokes that **follow the surface curvature**. The belly gets curved horizontal lines that bow outward (wrapping around the cylinder). Legs get lines that wrap around the tapered tube.

```python
def hatch_region(cx, cy, w, h, angle_deg, n_lines, curve=0, t=0.08):
    """Generate hatching strokes across a region.
    curve > 0 makes lines bow outward (wrapping around a form)."""
    angle = math.radians(angle_deg)
    dx, dy = math.cos(angle), math.sin(angle)
    px, py = -dy, dx  # perpendicular for spacing

    lines = []
    for i in range(n_lines):
        frac = (i / max(n_lines-1, 1)) - 0.5
        sx = cx + px * w * frac
        sy = cy + py * h * frac
        half_len = h * 0.4 * (1 - abs(frac) * 0.6)  # elliptical falloff

        if curve > 0:
            bow = curve * frac
            pts = [(sx - dx*half_len, sy - dy*half_len),
                   (sx + bow*px, sy + bow*py),
                   (sx + dx*half_len, sy + dy*half_len)]
        else:
            pts = [(sx - dx*half_len, sy - dy*half_len),
                   (sx + dx*half_len, sy + dy*half_len)]
        lines.append((smooth_pts(pts), t))
    return lines
```

### Cross-Hatching for Density

For darker areas, add a second pass of hatching at a different angle over the same region. This is how pencil drawings build up tonal density — multiple layers of hatching.

### Tonal Density Encodes Emotion

From the happy/angry analysis:
- **Happy figures**: sparse hatching (5 belly lines, 3 head lines), lighter overall
- **Angry figures**: dense hatching (9 belly lines + 6 cross-hatch, hatching in all limbs), darker and heavier

## Multi-Threshold Tonal Palette

### Four Darkness Bands From Analysis

Each band maps to a drawing layer and a pencil color:

| Band | Pencil Role | Happy Color | Angry Color |
|------|------------|-------------|-------------|
| Faint | Construction underdrawing | RGB(185,185,200) | RGB(150,150,165) |
| Light | Hatching, form shading | RGB(150,150,170) | RGB(110,110,130) |
| Medium | Defining contour outlines | RGB(95,95,120) | RGB(45,45,65) |
| Heavy | Emphasis marks at joints | RGB(50,50,70) | RGB(25,25,40) |

Angry figures use darker colors at every band — overall heavier hand.

### Pressure Profile Differences

From analyzing 24 gesture poses:

| Metric | Happy | Angry | Drawing Implication |
|--------|-------|-------|-------------------|
| Heavy marks | 52 | 88 (+69%) | Angry gets more emphasis marks |
| Curvature | 21.2° | 24.1° | Angry strokes are more angular |
| V/H energy | 1.36 | 1.12 | Happy is more vertical (bouncy) |
| Upward strokes | 26% | 22.5% | Happy reaches up more |
| Weight center | 0.55 | 0.48 | Happy is lifted, angry is grounded |
| Aspect ratio | 0.71 | 0.68 | Happy is wider (open pose) |

### Applying the Profile to New Drawings

**Happy pose:**
- Upright torso, higher center of gravity
- Arms reaching up, open body language
- One leg dynamic (kicked back)
- Sparse light hatching, fewer emphasis marks
- Rounder contour curvature

**Angry pose:**
- Hunched forward, lower weight center
- Wide grounded stance
- One fist raised, one clenched low
- Dense cross-hatching especially on belly/torso
- More angular contours
- Many heavy emphasis marks at joints and fists

## Drawing Layer Order

Build the figure in this order (bottom to top in visual stack):

1. **Faint construction** — broad sweeping gesture lines establishing the pose
2. **Light hatching** — curved form-following strokes that fill volumes with tone
3. **Cross-hatching** (angry/dense areas only) — second hatching pass at different angle
4. **Medium contour outlines** — the defining silhouette edges of all forms
5. **Heavy emphasis** — short dark marks at key structural points (joints, endpoints, tension areas)

## Thickness Scale Reference

In stage coordinates at typical camera sizes (280x180):
- Contour outlines: 0.10 - 0.15 (happy lighter, angry heavier)
- Hatching strokes: 0.05 - 0.08
- Emphasis marks: 0.10 - 0.16
- Construction strokes: use higher thickness (0.30-0.60) with faint color, not thicker line weight
