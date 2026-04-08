# Workflow 05: Reference Analysis & Style Learning

Vectorize reference artwork to extract structural and stylistic data, then use that data to inform new drawings or reproduce the original.

## Concepts

**Centerline vectorizer** extracts the **anatomy** of a drawing: the medial axis (skeleton) of each form, with thickness encoding the width of the form at each point. A limb becomes a single stroke whose thickness tapers. A body becomes a long stroke that's thick in the middle and thin at the edges. This is structural information — where things are and how wide they are — not how the artist drew them.

**Outline vectorizer** extracts the **actual contours** — the edges the viewer sees. Each ink line produces two contour strokes (inner and outer edge). Closed contours define fillable regions. With `preservePaintedAreas = true` and a clean color-quantized input, the outline vectorizer also detects and assigns colors to strokes.

Neither vectorizer captures artist intent, stroke direction, or drawing order. They decompose a finished image into geometric data.

## Pipeline

### Step 1: Perceptual Color Quantization

JPEG artifacts and gradients confuse the outline vectorizer's color detection. Pre-process the reference to flatten it into clean solid colors using perceptual clustering (k-means on foreground pixels):

```python
from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist

img = Image.open('reference.jpg').convert('RGB')
arr = np.array(img)

# Exclude near-white background from palette extraction
mask = ~((arr[:,:,0] > 230) & (arr[:,:,1] > 230) & (arr[:,:,2] > 230))
fg_pixels = arr[mask]

# Cluster foreground colors
kmeans = KMeans(n_clusters=10, random_state=42, n_init=10)
kmeans.fit(fg_pixels)
centers = sorted(kmeans.cluster_centers_.astype(int).tolist(), key=sum)

# Add black and white explicitly
palette = [[0,0,0]] + centers + [[255,255,255]]

# Map every pixel to nearest palette color
flat = arr.reshape(-1, 3).astype(float)
indices = cdist(flat, np.array(palette, dtype=float)).argmin(axis=1)
mapped = np.array(palette, dtype=np.uint8)[indices].reshape(arr.shape)
Image.fromarray(mapped).save('reference_quantized.png')
```

Why not use `STD_posterizeFx`? The posterize effect quantizes each RGB channel independently, which creates color bands that don't match the original palette. K-means clustering in perceptual space preserves the actual colors in the image (skin tones, specific yellows, etc.). The posterize effect is available and works through the headless API effect chain, but produces worse color fidelity for this use case.

### Step 2: Two-Pass Vectorization

A single vectorizer pass can't capture both ink lines and color fills well. Use two passes and composite them:

**Pass 1 — Outline (color fills):**
```javascript
var img = new Image();
img.load("reference_quantized.png");

var ov = new OutlineVectorizer();
ov.accuracy = 8;
ov.despeckling = 10;
ov.cornerAdherence = 60;
ov.cornerAngle = 50;
ov.maxColors = 25;
ov.preservePaintedAreas = true;  // REQUIRED for color detection
var fillImg = ov.vectorize(img);
```

**Pass 2 — Centerline (ink skeleton):**
```javascript
var cv = new CenterlineVectorizer();
cv.threshold = 8;        // higher = stricter ink/paper separation
cv.accuracy = 8;
cv.maxThickness = 30;    // cap to avoid filling dark regions as ink
cv.despeckling = 5;
var inkImg = cv.vectorize(img);
```

**Composite — fills on bottom, ink on top:**
```javascript
var scene = new Scene();
scene.setCameraSize(960, 840);  // slightly larger than image to avoid clipping

var fillLevel = scene.newLevel("Vector", "fills");
fillLevel.setFrame(1, fillImg);
scene.setCell(0, 0, fillLevel, 1);

var inkLevel = scene.newLevel("Vector", "ink");
inkLevel.setFrame(1, inkImg);
scene.setCell(0, 1, inkLevel, 1);  // column 1 = on top

var r = new Renderer();
var result = r.renderFrame(scene, 0);
result.save("reconstructed.png");
```

### Step 3: Extract Stroke Data

Once vectorized, extract the geometric data for analysis:

```javascript
var vi = fillImg.toVectorImage();
var data = [];
for (var i = 0; i < vi.strokeCount; i++) {
    var s = vi.getStroke(i);
    var pts = [];
    for (var j = 0; j < s.pointCount; j++) {
        var p = s.getPoint(j);
        pts.push([p[0], p[1], p[2]]);  // x, y, thickness
    }
    data.push({
        style: s.style,
        length: s.length,
        pointCount: s.pointCount,
        points: pts
    });
}
print(JSON.stringify(data));
```

### Step 4: Build a Style Profile

From the extracted data, compute statistics that characterize the drawing style:

- **Stroke count** — economy of the drawing (how many strokes per character)
- **Length distribution** — short/medium/long stroke ratios
- **Thickness profile** — uniform vs. tapered, average width, variation
- **Curvature** — angle between consecutive segments (low = smooth curves, high = angular)
- **Shape vocabulary** — ratio of round/tall/wide closed contours
- **Spatial extent** — bounding box, proportional relationships

From centerline specifically:
- **Anatomy** — skeleton positions reveal the internal structure (center of limbs, spine of body, form width at each point)
- **Form hierarchy** — longest strokes are the main body masses, short strokes are details

### Step 5: Synthesize New Drawings

Use the profile to generate new drawings. The key insight: draw from **understanding**, not data replay.

- Use centerline anatomy as a construction skeleton (where forms are, how wide)
- Use outline curvature/smoothness profiles to guide contour drawing
- Use the style's stroke weight, economy, and shape vocabulary as constraints
- Build closed contours for fillable regions, then apply fills

```javascript
// Example: draw a character body from anatomical understanding
var vi = new VectorImage();
var pal = new Palette();
var ink = pal.addColor(0,0,0,255);
var fill = pal.addColor(240,195,50,255);
vi.setPalette(pal);

// Body outline — smooth closed contour matching style's curvature profile
var body = new Stroke();
body.addPoints([/* control points derived from anatomy */]);
body.build();
body.close();
body.setStyle(ink);
vi.addStroke(body);

// Fill the body
vi.fill(0, 0, fill);
```

## Multi-Threshold Tonal Analysis (Pencil / Graphite)

For pencil drawings, a single vectorization pass loses tonal information — all strokes become the same darkness. By vectorizing at multiple thresholds and diffing the results, you recover the artist's pressure profile.

### Concept

The centerline vectorizer's `threshold` parameter controls ink/paper separation. At low threshold (strict), only the darkest marks register. At high threshold (permissive), lighter strokes appear too. By running multiple passes and identifying which strokes are **new** at each threshold, you get darkness bands:

| Band | Threshold | Captures |
|------|-----------|----------|
| Heavy pressure | 2 | Darkest marks only — emphasis points, joints, stroke endpoints |
| Normal pressure | 4 | Main defining strokes — the bulk of the drawing |
| Light pressure | 6 | Soft connecting strokes, curves, secondary forms |
| Construction | 8 | Ghost lines, underdrawing, paper texture |

### Step 1: Vectorize at Each Threshold

```javascript
var img = new Image();
img.load("pencil_drawing.jpg");

var thresholds = [2, 4, 6, 8];
var results = {};  // threshold -> stroke data

for (var t = 0; t < thresholds.length; t++) {
    var cv = new CenterlineVectorizer();
    cv.threshold = thresholds[t];
    cv.accuracy = 8;
    cv.maxThickness = 50;
    cv.despeckling = 5;
    var vimg = cv.vectorize(img);
    var vi = vimg.toVectorImage();
    // ... extract stroke data from vi
}
```

### Step 2: Compute Differential Bands

Each threshold captures all strokes at or above that darkness. Diff adjacent passes to isolate strokes unique to each band:

```python
def stroke_sig(s):
    """Spatial signature for matching strokes across passes."""
    pts = s['p']
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    return (round(cx/3)*3, round(cy/3)*3, round(s['l']/5)*5)

prev_sigs = set()
bands = {}
for t in [2, 4, 6, 8]:
    curr_sigs = {stroke_sig(s): s for s in passes[t]}
    bands[t] = [s for sig, s in curr_sigs.items() if sig not in prev_sigs]
    prev_sigs.update(curr_sigs.keys())
```

### Step 3: Render with Tonal Colors

Assign each band a gray level and build a single VectorImage:

```javascript
var vi = new VectorImage();
var pal = new Palette();
var heavy  = pal.addColor(30, 30, 40, 255);    // near-black
var medium = pal.addColor(80, 80, 95, 255);    // dark gray
var light  = pal.addColor(150, 150, 160, 255); // medium gray
var faint  = pal.addColor(200, 200, 210, 255); // light gray
vi.setPalette(pal);

// Add strokes from each band with appropriate style
// Heavy band strokes -> heavy style, etc.
```

### What the Bands Reveal

Pencil pressure analysis from a gesture study sheet (24 figure poses):

| Band | Strokes | Avg Thickness | Avg Length | Interpretation |
|------|---------|--------------|------------|----------------|
| Heavy | 161 | 0.07 | 2.5 | Short concentrated marks — the artist presses hard at key structural points |
| Medium | 482 | 0.13 | 3.9 | Normal drawing strokes — the main forms |
| Light | 358 | 0.21 | 4.2 | Flowing connecting curves — softer, more exploratory |
| Faint | 242 | 0.32 | 4.2 | Construction and underdrawing — broad soft graphite |

The pattern: heavier pressure produces shorter, thinner centerlines (concentrated dark marks), lighter pressure produces longer, wider centerlines (broad soft graphite deposits). This is a measurable pencil pressure profile.

### Use Cases

- **Pressure profiling** — learn where an artist applies emphasis (joints? endpoints? contour peaks?)
- **Construction vs. finished line** — the faint band shows the underdrawing skeleton, medium/heavy show the finished drawing
- **Style comparison** — compare pressure distributions across different artists or different poses
- **Pencil simulation** — use the band statistics to parameterize a synthetic pencil tool

## Effect Chain Integration

The headless API supports the full OpenToonz FX pipeline. Effects use `STD_` prefix:

```javascript
var fx = new Effect("STD_posterizeFx");
fx.setParam("levels", 5);
scene.connectEffect(0, fx);  // attach to column 0
```

Useful effects for reference processing:
- `STD_posterizeFx` — color quantization (levels parameter)
- `STD_blurFx` — smooth noise before vectorization
- `STD_despeckleFx` — remove small artifacts

Effects are applied during rendering — the vectorizer receives the processed output.

## Known Limitations

**Centerline can't distinguish ink from dark fills.** Dark-colored regions (mouths, dark eyes) register as thick ink strokes. Mitigate with `maxThickness` cap and higher `threshold`, but some bleed is unavoidable. A preprocessing step to separate ink from fill (e.g., edge detection to isolate thin lines) would improve this.

**Outline vectorizer needs clean color input.** JPEG artifacts, anti-aliasing gradients, and subtle color variations all create noise. Perceptual quantization is essential. The `preservePaintedAreas` flag must be `true` for color detection.

**Camera sizing.** The vectorizer applies a DPI-based coordinate transform. Images with unknown DPI (dpi=0) default to 72dpi. The rendered camera may need to be ~15-20% larger than the image dimensions to avoid clipping.

**No artist intent.** Vectorization decomposes a finished image. It can't recover stroke order, drawing direction, or the artist's decision-making process. The centerline reveals anatomy, the outline reveals contours, but interpretation requires external knowledge (e.g., knowing a character has 2 legs, not 4).

## API Methods Used

| Method | Purpose |
|--------|---------|
| `Image.load(path)` | Load raster reference |
| `Effect(name)` / `setParam` | Apply FX (posterize, etc.) |
| `Scene.connectEffect(col, fx)` | Wire effect into render chain |
| `CenterlineVectorizer.vectorize(img)` | Extract ink skeleton |
| `OutlineVectorizer.vectorize(img)` | Extract colored contours |
| `Image.toVectorImage()` | Unwrap vector data for stroke access |
| `VectorImage.getStroke(i)` | Access individual strokes |
| `Stroke.getPoint(j)` | Read control point [x, y, thickness] |
| `Stroke.length` / `.pointCount` / `.style` | Stroke metrics |
| `Scene.setCameraSize(w, h)` | Set render dimensions |
| `Scene.newLevel` / `setCell` | Compose layers |
| `Renderer.renderFrame(scene, frame)` | Render composite |
