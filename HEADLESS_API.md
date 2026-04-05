# OpenToonz Headless API Reference

A programmatic interface to OpenToonz for creating 2D animation without a GUI. Communicates via JSON-RPC over stdin/stdout.

## Quick Start

```bash
# Binary location
/home/wipkat/opentoonz/toonz/sources/build/bin/toonz_headless

# Send JSON-RPC commands via stdin, read responses from stdout
echo '{"id":1,"method":"eval","params":{"code":"print(1+1)"}}' | toonz_headless
```

## Protocol

JSON-RPC 2.0 over stdin/stdout. One JSON object per line.

### Methods

| Method | Params | Description |
|--------|--------|-------------|
| `eval` | `{"code": "..."}` | Evaluate JavaScript code in the ScriptEngine |
| `ping` | `{}` | Health check, returns `"pong"` |
| `quit` | `{}` | Shutdown cleanly |

### Startup

On launch, the tool emits a ready notification:
```json
{"jsonrpc":"2.0","method":"ready","params":{"version":"1.0"}}
```

### Response Format

```json
{"jsonrpc":"2.0","id":1,"result":{"ok":true,"output":"..."}}
```

The `output` field contains whatever `print()` produced during evaluation. Errors from `throwError()` also appear in `output` prefixed with `"Error:"`.

### Important: State Persists

Each `eval` runs in the same ScriptEngine instance. Variables created in one eval are available in the next. The tool runs until `quit` is sent or stdin closes.

---

## Classes

### Stroke

Create vector strokes from point sequences.

```javascript
var s = new Stroke();
s.addPoint(x, y, thickness);           // Add single point
s.addPoints([[x,y,t], [x,y,t], ...]);  // Batch add (t = thickness, default 1.0)
s.build();                              // Finalize stroke geometry
s.close();                              // Make it a closed loop
s.setStyle(styleId);                    // Assign palette color (integer index)
```

**Properties:** `length` (double), `pointCount` (int), `style` (int)

**Notes:**
- Must call `build()` before using the stroke in a VectorImage
- Points define cubic Bezier control points — OpenToonz interpolates between them
- For smooth curves, use 3+ points. For sharp corners, place points close together
- Thickness is in stage units (roughly pixels at 72 DPI)

---

### VectorImage

Container for vector strokes and regions. The primary drawing surface for PLI levels.

```javascript
var vi = new VectorImage();

// Stroke operations
vi.addStroke(stroke);                   // Add a built Stroke object
vi.removeStroke(index);                 // Remove by index
vi.getStroke(index);                    // Get Stroke wrapper at index

// Geometric primitives (auto-generate multiple strokes for fillable shapes)
vi.addRect(x1, y1, x2, y2, thickness, styleId);
vi.addCircle(cx, cy, radius, thickness, styleId, segments);  // segments default 16
vi.addEllipse(cx, cy, rx, ry, thickness, styleId, segments);
vi.addPolygon(cx, cy, radius, sides, thickness, styleId);
vi.addLine(x1, y1, x2, y2, thickness, styleId);

// Fill operations (requires regions formed by closed/intersecting strokes)
vi.findRegions();                       // Compute regions explicitly before fill
vi.fill(x, y, styleId);                // Flood fill region at point
vi.setEdgeColors(strokeIdx, left, right); // Set boundary colors

// Grouping
vi.group(fromIndex, count);             // Group consecutive strokes
vi.ungroup(index);                      // Ungroup

// Merging
vi.merge(otherVectorImage);             // Merge another VectorImage into this one

// Palette (MUST set before rasterizing or saving)
vi.setPalette(palette);                 // Assign a Palette object

// Convert to Image for use with Level.setFrame()
var img = vi.toImage();
```

**Properties:** `strokeCount` (int), `regionCount` (int)

**Critical:** You MUST call `vi.setPalette(pal)` before calling `toImage()` or rasterizing. Without a palette, the Rasterizer will error with "Vector image has no palette".

---

### RasterCanvas

CPU-based raster drawing surface for TZP (Toonz Raster) levels. No GPU required.

```javascript
var rc = new RasterCanvas(width, height);  // Create canvas (pixels)

// Drawing
rc.brushStroke([[x,y,t], ...], styleId, antialias);  // Draw brush stroke
rc.fill(x, y, styleId);                  // Flood fill at point
rc.rectFill(x1, y1, x2, y2, styleId);   // Fill rectangle (works on blank canvas)
rc.inkFill(x, y, styleId, searchRay);    // Fill ink lines at point
rc.clear();                               // Clear canvas

// Palette (needed for colored output)
rc.setPalette(palette);                   // Set palette for colored ToonzRaster output

// Convert to Image
var img = rc.toImage();                   // Returns ToonzRaster Image
```

**Properties:** `width` (int), `height` (int)

**Notes:**
- Coordinates are in pixels, origin at bottom-left
- styleId references palette colors (ink = style index for line color)
- The brush stroke points should be dense enough for smooth curves
- antialias parameter (boolean) controls edge smoothing
- `rectFill()` writes paint values directly — works on blank/cleared canvases

---

### Palette

Color management. Each style has a global integer ID used by strokes and fills.

```javascript
var pal = new Palette();
pal.addPage("Page Name");               // Organize colors into pages

// Solid colors
var styleId = pal.addColor(r, g, b, a); // Add color, returns GLOBAL style ID
pal.setStyleColor(styleId, r, g, b, a); // Modify existing color
var c = pal.getStyleColor(styleId);      // Returns {r, g, b, a}

// Advanced styles (gradients, patterns, textures, decorative strokes)
var sid = pal.addStyle(tagId);           // Create style by tag ID
pal.getStyleType(styleIdx);              // Returns {tagId, description, isRegionStyle, isStrokeStyle}
pal.getStyleParamNames(styleIdx);        // Array of {name, type} for each param
pal.setStyleParam(styleIdx, paramIdx, value);
pal.getStyleParam(styleIdx, paramIdx);
pal.setStyleColorParam(styleIdx, colorIdx, r, g, b, a);
pal.getStyleColorParam(styleIdx, colorIdx);
pal.getAvailableTags();                  // List all 53 style types with metadata

// Color model (reference image for color picking)
pal.loadColorModel(path);               // Load reference image (PNG, etc.)
var c = pal.pickColorFromModel(x, y);   // Returns {r, g, b, a, closestStyleId}
pal.removeColorModel();                  // Clear reference image
```

**Properties:** `styleCount` (int), `pageCount` (int)

**Important:**
- A new Palette starts with 2 default styles (indices 0 and 1 — typically transparent and black)
- `addColor()` returns the global style ID (usually starting at 2)
- Palettes start with 1 default page ("colors") — no need to call `addPage()` first
- Color components are integers 0-255
- Use `getAvailableTags()` to discover all style types (1138 = linear gradient, 1139 = radial gradient, etc.)

---

### Scene (built-in, extended)

Manage scenes, levels, and the XSheet timeline.

```javascript
var scene = new Scene();

// Level management
var level = scene.newLevel("Vector", "level_name");    // "Vector", "ToonzRaster", or "Raster"
var level = scene.loadLevel("name", path);
var levels = scene.getLevels();
var level = scene.getLevel("name");

// XSheet cells
scene.setCell(row, col, level, frameId);  // Place a frame in the timeline
scene.getCell(row, col);                   // Returns {level, fid}
scene.insertColumn(col);
scene.deleteColumn(col);

// Stage objects
var obj = scene.getStageObject(colIdx);    // Get StageObject for column

// FX graph
scene.connectEffect(colIdx, effect);       // Wire column → effect → xsheet output

// Camera
scene.setCameraSize(width, height);        // Set camera resolution in pixels
var cam = scene.getCameraSize();           // Returns {width, height}

// Motion path splines
var splineIdx = scene.createSpline([[x,y], [x,y], ...]);  // Min 3 control points

// Settings
scene.setFrameRate(fps);                   // Set output frame rate

// File I/O
scene.load(path);
scene.save(path);
```

**Properties:** `frameCount` (int), `columnCount` (int)

---

### Level (built-in, extended)

Manage drawing levels (collections of frames).

```javascript
var level = new Level();

// Frame operations
level.setFrame(frameId, image);           // Set frame content (frameId: number or "1a" string)
var img = level.getFrame(frameId);
var img = level.getFrameByIndex(index);
var fids = level.getFrameIds();           // Array of frame ID strings

// Palette
level.setPalette(palette);                // Assign palette to level
var pal = level.getPalette();             // Get level's palette

// Drawing hooks (attachment points for cut-out animation)
var hookIdx = level.addHook(frameId, x, y);  // Add hook at position, returns index
var hooks = level.getHooks(frameId);         // Returns array of {index, x, y}
level.removeHook(hookIdx);                   // Remove hook by index

// File I/O
level.load(path);
level.save(path);                         // .pli for vector, .tlv for toonz raster, .png/.tif for raster
```

**Properties:** `type` (string), `frameCount` (int), `name` (string r/w), `path` (r/w)

---

### Image (built-in)

Wrapper around a single frame image. Created by `VectorImage.toImage()`, `RasterCanvas.toImage()`, `Level.getFrame()`, etc.

```javascript
var img = new Image();
img.load(path);
img.save(path);
```

**Properties:** `type` (string: "Vector", "ToonzRaster", "Raster"), `width` (int), `height` (int), `dpi` (double)

---

### StageObject

Animate position, rotation, scale per column. Supports bone hierarchy, IK, and motion paths.

```javascript
var obj = scene.getStageObject(colIdx);   // Cannot create directly

// Keyframing
obj.setKeyframe(frame, channel, value);
obj.getValueAt(frame, channel);
obj.setInterpolation(frame, channel, type);

// Hierarchy
obj.setParent(otherStageObject);
obj.setStatus(statusString);              // "xy", "path", "pathAim", "ik"

// Motion path
obj.setSpline(splineIdx);                 // Assign spline from scene.createSpline()

// Inverse kinematics
var angles = obj.solveIK(targetX, targetY, frame);
// Walks parent chain, solves IK (DLS, 250 iterations), applies angle
// keyframes to each joint. Returns array of solved angles.
```

**Channels:** `"x"`, `"y"`, `"z"`, `"angle"` (or `"rotation"`), `"scalex"`, `"scaley"`, `"scale"`, `"shearx"`, `"sheary"`, `"so"` (stacking order), `"path"`

**Interpolation types:** `"constant"`, `"linear"`, `"speedInOut"` (bezier), `"easeInOut"`, `"exponential"`

**Properties:** `name` (string r/w), `status` (string)

---

### Inbetween

Auto-generate intermediate vector frames between two key drawings.

```javascript
// Both images must be Vector type with matching stroke structure
var tween = new Inbetween(vectorImage1, vectorImage2);
var mid = tween.tween(0.5, "linear");     // t in [0,1], returns new Image
```

**Easing options:** `"linear"`, `"easeIn"`, `"easeOut"`, `"easeInOut"`

**Limitation:** Vector (PLI) images only. Both images should have the same number of strokes for best results.

---

### PlasticRig

Mesh-based skeleton for deformation animation.

```javascript
var rig = new PlasticRig();

// Build skeleton hierarchy
var root = rig.addVertex(x, y, -1);       // -1 = no parent (root)
var child = rig.addVertex(x, y, root);    // parent index
rig.moveVertex(vertexIdx, newX, newY);
rig.removeVertex(vertexIdx);
rig.setVertexName(vertexIdx, "name");

// Animate deformation
rig.setVertexKeyframe(vertexIdx, frame, param, value);
```

**Params:** `"angle"` (rotation from parent), `"distance"` (from parent), `"so"` (stacking order)

**Properties:** `vertexCount` (int)

**Note:** The skeleton is automatically attached to the deformation system — `addVertex()` creates vertex deformation entries so `setVertexKeyframe()` works immediately.

---

### Effect

Create and configure any of the 145 built-in OpenToonz effects.

```javascript
var fx = new Effect("STD_particlesFx");   // MUST include STD_ prefix

// Parameters
var names = fx.getParamNames();           // Array of parameter name strings
fx.setParam(name, value);                 // Set default value
var v = fx.getParam(name);                // Read current value
fx.setParamKeyframe(name, frame, value);  // Animate parameter
```

**Properties:** `type` (string), `paramCount` (int)

**Common effect identifiers** (all prefixed with `STD_`):

| Effect | Identifier | Notable Params |
|--------|-----------|---------------|
| Particles | `STD_particlesFx` | birth_rate, lifetime, gravity_val, wind_intensity (73 params) |
| Blur | `STD_blurFx` | value |
| Directional Blur | `STD_directionalBlurFx` | value, angle |
| Glow | `STD_glowFx` | value, color |
| Brightness/Contrast | `STD_brightContFx` | brightness, contrast |
| Color Card | `STD_colorCardFx` | color |
| Radial Gradient | `STD_radialGradientFx` | color, size |
| Fade | `STD_fadeFx` | value |

Use `fx.getParamNames()` to discover all parameters for any effect.

**Connecting to scene:** Use `scene.connectEffect(colIdx, effect)` to wire a column through an effect into the xsheet output.

---

### Rasterizer (built-in)

Convert vector images/levels to raster PNG output.

```javascript
var rast = new Rasterizer();
rast.xres = 512;                          // Output width in pixels
rast.yres = 512;                          // Output height in pixels
rast.dpi = 72;                            // Resolution
rast.antialiasing = true;

var rasterImg = rast.rasterize(vectorImage);  // Returns raster Image
rasterImg.save("/path/to/output.png");
```

Can also rasterize entire levels:
```javascript
var rasterLevel = rast.rasterize(vectorLevel);
```

---

### Renderer (built-in)

Render complete scenes (compositing all layers, effects, camera). Works in headless mode.

```javascript
var renderer = new Renderer();
var singleFrame = renderer.renderFrame(scene, frameNumber);  // Returns raster Image
var outputLevel = renderer.renderScene(scene);                // Returns Level with all frames
```

**Tips:**
- Set camera size first: `scene.setCameraSize(1920, 1080)` controls output resolution
- The returned Image may show "Empty" in `toString()` on the same eval due to async timing — access `type`/`width`/`height` in the next eval for correct values
- Rendering uses the TRenderer thread pool with proper event loop handling

---

### Transform (built-in)

2D affine transformations for use with ImageBuilder.

```javascript
var t = new Transform();
t.translate(dx, dy);
t.rotate(degrees);
t.scale(factor);
t.scale(sx, sy);
```

---

### ImageBuilder (built-in)

Composite existing images with transformations.

```javascript
var builder = new ImageBuilder();
builder.add(image);
builder.add(image, transform);
builder.fill("red");                      // Named color or hex "#FF0000"
builder.clear();
var result = builder.image;               // Get composited Image
```

---

## Complete Workflow Examples

### Draw a Character and Save as PNG

```javascript
// 1. Create palette
var pal = new Palette();
pal.addPage("Character");
var ink = pal.addColor(40, 40, 40, 255);      // Dark gray outline
var skin = pal.addColor(255, 210, 180, 255);   // Skin tone
var hair = pal.addColor(80, 50, 30, 255);      // Dark brown

// 2. Draw character
var vi = new VectorImage();

// Head (closed oval)
var head = new Stroke();
head.addPoints([[-25,60,2],[-20,80,2],[0,90,2],[20,80,2],
                [25,60,2],[20,40,2],[0,30,2],[-20,40,2],[-25,60,2]]);
head.build(); head.close(); head.setStyle(ink);
vi.addStroke(head);

// Body
var body = new Stroke();
body.addPoints([[-20,30,2],[-25,-20,2],[-15,-60,2],
                [0,-70,2],[15,-60,2],[25,-20,2],[20,30,2]]);
body.build(); body.setStyle(ink);
vi.addStroke(body);

// Arms
var larm = new Stroke(); larm.addPoints([[-25,10,2],[-55,-25,2]]);
larm.build(); larm.setStyle(ink); vi.addStroke(larm);
var rarm = new Stroke(); rarm.addPoints([[25,10,2],[55,-25,2]]);
rarm.build(); rarm.setStyle(ink); vi.addStroke(rarm);

// Legs
var lleg = new Stroke(); lleg.addPoints([[-15,-60,2],[-20,-120,2]]);
lleg.build(); lleg.setStyle(ink); vi.addStroke(lleg);
var rleg = new Stroke(); rleg.addPoints([[15,-60,2],[20,-120,2]]);
rleg.build(); rleg.setStyle(ink); vi.addStroke(rleg);

// 3. Assign palette and rasterize
vi.setPalette(pal);
var img = vi.toImage();
var rast = new Rasterizer();
rast.xres = 512; rast.yres = 512; rast.dpi = 72;
rast.rasterize(img).save("/tmp/character.png");
```

### Animate with Auto-Inbetween

```javascript
// Create palette
var pal = new Palette(); pal.addPage("ink");
var ink = pal.addColor(0, 0, 0, 255);

// Key frame 1: arm up
var vi1 = new VectorImage();
var s1 = new Stroke();
s1.addPoints([[0,0,3],[0,80,3],[-40,120,3]]);
s1.build(); s1.setStyle(ink); vi1.addStroke(s1);
vi1.setPalette(pal);

// Key frame 2: arm down
var vi2 = new VectorImage();
var s2 = new Stroke();
s2.addPoints([[0,0,3],[0,80,3],[40,40,3]]);
s2.build(); s2.setStyle(ink); vi2.addStroke(s2);
vi2.setPalette(pal);

// Generate inbetweens
var img1 = vi1.toImage();
var img2 = vi2.toImage();
var tw = new Inbetween(img1, img2);

// Render 5 frames
var rast = new Rasterizer();
rast.xres = 256; rast.yres = 256; rast.dpi = 72;
for (var i = 0; i <= 4; i++) {
    var t = i / 4.0;
    var frame = (i == 0) ? img1 : (i == 4) ? img2 : tw.tween(t, "easeInOut");
    rast.rasterize(frame).save("/tmp/frame_" + i + ".png");
}
```

### Build an Animated Scene with Keyframes

```javascript
// Create scene and level
var scene = new Scene();
var level = scene.newLevel("Vector", "bouncing_ball");

// Create a circle drawing
var pal = new Palette(); pal.addPage("ball");
var outline = pal.addColor(0, 0, 0, 255);
var vi = new VectorImage();
var circle = new Stroke();
circle.addPoints([[-30,0,2],[0,30,2],[30,0,2],[0,-30,2],[-30,0,2]]);
circle.build(); circle.close(); circle.setStyle(outline);
vi.addStroke(circle);
vi.setPalette(pal);

// Set the same drawing on every frame (it's a hold)
level.setFrame(1, vi.toImage());
for (var f = 1; f <= 24; f++) {
    scene.setCell(f-1, 0, level, 1);
}

// Animate position: bounce
var obj = scene.getStageObject(0);
obj.setKeyframe(0, "y", 0);
obj.setKeyframe(12, "y", 100);
obj.setKeyframe(24, "y", 0);
obj.setInterpolation(0, "y", "easeInOut");
obj.setInterpolation(12, "y", "easeInOut");

// Set frame rate
scene.setFrameRate(24);
```

### Render a Scene to PNG

```javascript
// 1. Create scene with camera
var scene = new Scene();
scene.setCameraSize(512, 512);

// 2. Create content
var level = scene.newLevel("Vector", "ball");
var pal = new Palette();
var ink = pal.addColor(0, 0, 0, 255);
var vi = new VectorImage();
vi.addCircle(0, 0, 40, 2, ink);          // Geometric primitive
vi.setPalette(pal);
level.setFrame(1, vi.toImage());
scene.setCell(0, 0, level, 1);

// 3. Render
var renderer = new Renderer();
var img = renderer.renderFrame(scene, 0);
// Access properties in next eval due to async timing
```
```javascript
img.save("/tmp/rendered_ball.png");
```

### Render with Effects

```javascript
var scene = new Scene();
scene.setCameraSize(256, 256);
var lv = scene.newLevel("Vector", "fx_demo");
var pal = new Palette(); var ink = pal.addColor(0, 0, 0, 255);
var vi = new VectorImage();
vi.addRect(-50, -5, 50, 5, 2, ink);
vi.setPalette(pal);
lv.setFrame(1, vi.toImage());
scene.setCell(0, 0, lv, 1);

// Apply blur effect to column 0
var blur = new Effect("STD_blurFx");
blur.setParam("value", 10);
scene.connectEffect(0, blur);

var renderer = new Renderer();
var img = renderer.renderFrame(scene, 0);
```

### Create a Particle Effect

```javascript
var fx = new Effect("STD_particlesFx");

// Configure particle system
fx.setParam("birth_rate", 20);
fx.setParam("lifetime", 50);
fx.setParam("length", 100);
fx.setParam("height", 100);

// Animate wind
fx.setParamKeyframe("wind_intensity", 0, 0);
fx.setParamKeyframe("wind_intensity", 48, 30);

// List all available parameters
var names = fx.getParamNames();
print(names.length + " parameters available");
```

---

## Gotchas and Tips

1. **Palette must be set before rasterizing.** Call `vi.setPalette(pal)` before `vi.toImage()` or rasterizing.

2. **Style IDs start at 2.** New palettes have 2 default styles (0 and 1). Your first `addColor()` returns index 2.

3. **Effect identifiers need `STD_` prefix.** Use `"STD_particlesFx"`, not `"particlesFx"`.

4. **Level type strings are capitalized.** Use `"Vector"`, `"ToonzRaster"`, `"Raster"` — not lowercase.

5. **Variables persist between eval calls.** Each `eval` runs in the same JS context. Variables from previous evals are available.

6. **Coordinates:** Vector images use stage coordinates centered at (0,0). Raster canvases use pixel coordinates with origin at bottom-left.

7. **Inbetween only works on vector images.** Both images should have matching stroke counts for clean results.

8. **StageObject cannot be created directly.** Always get it via `scene.getStageObject(colIdx)`.

9. **Stroke.build() is required.** After adding points, call `build()` to finalize the geometry before using the stroke.

10. **Save format determined by extension.** `.pli` = vector, `.tlv` = toonz raster, `.png`/`.tif` = full color raster.

11. **Fillable regions require multiple strokes.** A single closed stroke (`stroke.close()`) does **not** create a fillable region. OpenToonz computes regions from intersections between separate strokes. To create a fillable shape, draw it as multiple strokes sharing endpoints:

    ```javascript
    // WRONG — single self-loop, fill() will fail (0 regions)
    var s = new Stroke();
    s.addPoints([[-50,-50,2],[50,-50,2],[50,50,2],[-50,50,2],[-50,-50,2]]);
    s.build(); s.close(); s.setStyle(ink);
    vi.addStroke(s);
    vi.fill(0, 0, red); // Error: no region found

    // CORRECT — 4 edge strokes, fill() works (1 region)
    var top = new Stroke(); top.addPoints([[-50,-50,2],[50,-50,2]]); top.build(); top.setStyle(ink); vi.addStroke(top);
    var right = new Stroke(); right.addPoints([[50,-50,2],[50,50,2]]); right.build(); right.setStyle(ink); vi.addStroke(right);
    var bottom = new Stroke(); bottom.addPoints([[50,50,2],[-50,50,2]]); bottom.build(); bottom.setStyle(ink); vi.addStroke(bottom);
    var left = new Stroke(); left.addPoints([[-50,50,2],[-50,-50,2]]); left.build(); left.setStyle(ink); vi.addStroke(left);
    vi.fill(0, 0, red); // OK — fills the enclosed region
    ```

12. **Points are Bezier control points, not polygon vertices.** Strokes interpolate smoothly between points. A single stroke with 4 points will render as a smooth curve, not a square. For sharp corners, use separate strokes — one per edge — meeting at the corner point. For smooth curves like circles, use more points on a single stroke (16+ for a clean circle).

13. **RasterCanvas requires a palette for colored output.** Call `rc.setPalette(pal)` before `toImage()` to get colored PNG output. Without a palette, only style 1 (default black) is visible.

---

## Binary Location and Build

```
Binary:  /home/wipkat/opentoonz/toonz/sources/build/bin/toonz_headless
Source:  /home/wipkat/opentoonz/toonz/sources/toonz_headless/main.cpp
Build:   cd toonz/sources/build && ninja toonz_headless
```

## Coordinate System

- **Vector images**: Stage coordinates, center at (0,0), units ≈ pixels at 72 DPI
- **Raster canvas**: Pixel coordinates, origin at bottom-left corner
- **Rasterizer**: Maps stage coordinates to output resolution via camera/DPI settings
