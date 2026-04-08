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

// Outline options (can set before or after build)
s.setCapStyle("butt");                  // "butt", "round" (default), "projecting"
s.setJoinStyle("miter");               // "miter", "round" (default), "bevel"
s.setMiterLimit(6.0);                  // Upper miter limit (default 4.0)
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

// Filled primitives (strokes + auto-fill in one call)
vi.addFilledRect(x1, y1, x2, y2, thickness, inkStyleId, fillStyleId);
vi.addFilledCircle(cx, cy, radius, thickness, inkStyleId, fillStyleId, segments);
vi.addFilledPolygon(cx, cy, radius, sides, thickness, inkStyleId, fillStyleId);
vi.addFilledEllipse(cx, cy, rx, ry, thickness, inkStyleId, fillStyleId, segments);
// Use inkStyleId=0 for invisible outlines (filled shape only)

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
rc.brushStroke([[x,y,t], ...], styleId, antialias);       // Draw brush stroke
rc.brushStroke([[x,y,t], ...], styleId, antialias, true); // Lock-alpha: only paint over existing ink
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
scene.removeLevel("name");                 // Remove level from scene (or pass Level object)

// XSheet cells
scene.setCell(row, col, level, frameId);  // Place a frame in the timeline
scene.getCell(row, col);                   // Returns {level, fid}
scene.insertColumn(col);
scene.deleteColumn(col);

// Column properties
scene.enableColumnOpacity(true);           // Must enable before opacity takes effect on render
scene.setColumnOpacity(col, opacity);      // 0-255
var opacity = scene.getColumnOpacity(col);

// Stage objects
var obj = scene.getStageObject(colIdx);    // Get StageObject for column

// FX graph
scene.connectEffect(colIdx, effect);       // Wire column → effect → xsheet output

// Camera
scene.setCameraSize(width, height);        // Set camera resolution in pixels
var cam = scene.getCameraSize();           // Returns {width, height}

// Mesh generation for plastic deformation
var meshLevel = scene.buildMesh(rasterImage, "mesh_name");  // Returns Level (MESH type)

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
obj.deleteKeyframe(frame, channel);
var count = obj.getKeyframeCount(channel);
var kfs = obj.getKeyframes(channel);       // [{frame, value, type}, ...]
obj.setExpression(frame, channel, "frame * 3");  // Expression-driven animation

// Hierarchy
obj.setParent(otherStageObject);
obj.setStatus(statusString);              // "xy", "path", "pathAim", "ik"

// Plastic deformation
obj.setPlasticRig(plasticRig);            // Attach PlasticRig deformation to this column

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

**Rendering plastic deformation** requires wiring up the full pipeline:
1. Build a mesh from the texture image: `scene.buildMesh(image, "meshName")`
2. Place the mesh in a column: `scene.setCell(0, meshCol, meshLevel, 1)`
3. Parent the texture column to the mesh column: `texObj.setParent(meshObj)`
4. Attach the rig to the mesh column: `meshObj.setPlasticRig(rig)`
5. Render — the deformer is injected automatically

See the [Plastic Deformation](#plastic-deformation) example below.

---

### Effect

Create and configure any of the 145 built-in OpenToonz effects.

```javascript
var fx = new Effect("STD_particlesFx");   // MUST include STD_ prefix

// Parameter access
var names = fx.getParamNames();           // Array of parameter name strings
var type = fx.getParamType(name);         // "double","int","bool","enum","point","pixel","range","string","filepath"
fx.setParam(name, value);                 // Set value (type auto-detected)
var v = fx.getParam(name);                // Read current value
fx.setParamKeyframe(name, frame, value);  // Animate (double/point/pixel/range only)

// Value types by parameter type:
fx.setParam("blur_value", 10.5);          // double/int — number
fx.setParam("use_sse", true);             // bool — boolean
fx.setParam("swing_mode", 2);             // enum — integer index
fx.setParam("center", [100, 50]);         // point — [x, y]
fx.setParam("color", [255, 0, 0, 255]);   // pixel — [r, g, b, a]
fx.setParam("lifetime", [20, 100]);       // range — [min, max]
fx.setParam("text", "hello");             // string — string
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
- Rendering is synchronous — `renderFrame()` and `renderScene()` block until complete and return the finished image in the same eval
- Rendering uses the TRenderer thread pool with proper cross-thread synchronization

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
fx.setParam("lifetime", [20, 100]);       // range: [min, max]
fx.setParam("length", 100);
fx.setParam("height", 100);

// Animate wind
fx.setParamKeyframe("wind_intensity", 0, 0);
fx.setParamKeyframe("wind_intensity", 48, 30);

// List all available parameters
var names = fx.getParamNames();
print(names.length + " parameters available");
```

### Plastic Deformation

```javascript
var scene = new Scene();
scene.setCameraSize(256, 256);

// 1. Create texture (a rectangle outline)
var texLevel = scene.newLevel("ToonzRaster", "texture");
var canvas = new RasterCanvas(256, 256);
canvas.brushStroke([[78,28,3],[178,28,3],[178,228,3],[78,228,3],[78,28,3]], 1, true);
texLevel.setFrame(1, canvas.toImage());
scene.setCell(0, 0, texLevel, 1);

// 2. Build mesh from texture
var texImg = texLevel.getFrame(1);
var meshLevel = scene.buildMesh(texImg, "mesh1");
scene.setCell(0, 1, meshLevel, 1);

// 3. Parent texture column to mesh column
var texObj  = scene.getStageObject(0);
var meshObj = scene.getStageObject(1);
texObj.setParent(meshObj);

// 4. Build rig and animate
var rig = new PlasticRig();
var root = rig.addVertex(0, 0);
var tip  = rig.addVertex(0, 80, root);
rig.setVertexKeyframe(tip, 0, "angle", 0);
rig.setVertexKeyframe(tip, 24, "angle", 30);
meshObj.setPlasticRig(rig);

// 5. Render deformed frame
var renderer = new Renderer();
var img = renderer.renderFrame(scene, 12);  // mid-animation
img.save("/tmp/plastic_deform.png");
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

11. **Fillable regions require multiple strokes** (or use `addFilledRect`/`addFilledCircle`/`addFilledPolygon`/`addFilledEllipse` which handle this automatically). A single closed stroke (`stroke.close()`) does **not** create a fillable region. OpenToonz computes regions from intersections between separate strokes. To create a fillable shape manually, draw it as multiple strokes sharing endpoints:

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

## Compositing/FX (Extended)

The FX graph can now be manipulated beyond single-column effects.

### Effect Port Introspection

```javascript
var fx = new Effect("STD_blurFx");
fx.inputPortCount;              // Number of input ports (1 for most filters)
fx.getInputPortName(0);         // Name of port 0 (e.g., "Source")

// Wire another effect to a specific input port
fx.connectInput(0, otherEffect);           // By index
fx.connectInput("Source", otherEffect);    // By name
fx.connectInput(0, null);                  // Disconnect
```

### Effect Chaining

Chain multiple effects on a single column:

```javascript
var scene = new Scene();
// ... create level, set cells ...

var blur = new Effect("STD_blurFx");
blur.setParam("value", 5);
var glow = new Effect("STD_glowFx");
glow.setParam("value", 10);

// Connect column 0 -> blur -> glow -> output
scene.connectEffect(0, blur);    // column -> blur (existing API)
scene.chainEffects(blur, glow);  // blur -> glow's first input port
```

### Blend Effects (Two-Column Compositing)

Blend two columns using any 2-input effect (over, multiply, add, etc.):

```javascript
// Create two columns with content
scene.setCell(0, 0, bgLevel, 1);
scene.setCell(0, 1, fgLevel, 1);

// Blend them
var blend = new Effect("STD_inoOverFx");  // Porter-Duff over
scene.connectBlend(0, 1, blend);          // col0 -> port0, col1 -> port1

// Other blend modes:
// "STD_inoAddFx", "STD_inoMultiplyFx", "STD_inoScreenFx",
// "STD_inoOverlayFx", "STD_inoCrossDissFx", etc.
```

### Disconnect and Query Effects

```javascript
scene.disconnectEffect(blur);    // Remove effect, reconnect upstream to output
var fx = scene.getColumnEffect(0); // Get effect connected to column 0 (or null)
```

---

## Rendering/Output (Extended)

### Renderer Properties

```javascript
var renderer = new Renderer();

// Resample quality (filter for affine transforms)
renderer.quality = "lanczos3";  // Options: "standard", "improved", "high",
                                // "triangle", "mitchell", "cubic5", "cubic75",
                                // "cubic1", "lanczos2", "lanczos3", "hann2",
                                // "hann3", "hamming2", "hamming3", "gauss",
                                // "closestPixel", "bilinear"

// Channel depth
renderer.channelWidth = 8;      // 8 (default) or 16 bits per channel

// Thread count
renderer.threadCount = 4;       // Number of render threads (default: 1)
```

### Render to File

Render a frame range directly to disk. Format determined by file extension.

```javascript
// Render frames 0-23 to PNG sequence
renderer.renderToFile(scene, "/output/anim..png", 0, 23, 1);

// Render every 2nd frame to TIF
renderer.renderToFile(scene, "/output/anim..tif", 0, 47, 2);

// Render single frame
renderer.renderToFile(scene, "/output/frame..png", 5, 5, 1);
```

**Supported formats:** PNG, TIF, TGA, JPG, BMP (image sequences). Format extensions with codec support (MOV, MP4) depend on system FFmpeg availability.

**Note:** The double-dot `..` in filenames is OpenToonz convention for frame number insertion (e.g., `anim..png` becomes `anim.0001.png`, `anim.0002.png`, etc.)

---

## Cleanupper

Process scanned or raster artwork into clean digital levels. Converts full-color raster images to ToonzRaster (indexed colormap) format with line processing, despeckling, and tonal normalization.

```javascript
var cl = new Cleanupper();

// Line processing mode
cl.lineProcessing = "greyscale";  // "none", "greyscale", "color"

// Sharpness and despeckling
cl.sharpness = 90;       // 0-100 (higher = sharper, default 90)
cl.despeckling = 2;      // 0-20 (speckle removal threshold, default 2)

// Antialiasing
cl.antialias = "standard";    // "standard", "none", "morphological"
cl.aaIntensity = 70;          // 0-100 (morphological AA intensity, default 70)

// Auto-adjust (greyscale mode only)
cl.autoAdjust = "none";  // "none", "blackEq", "histogram", "histoL"

// Geometric transforms
cl.rotate = 0;           // 0, 90, 180, 270
cl.flipX = false;
cl.flipY = false;

// Process a single image (Raster or ToonzRaster input -> ToonzRaster output)
var cleaned = cl.process(rasterImage);

// Process all frames in a level
var cleanedLevel = cl.processLevel(rasterLevel);
```

**Auto-adjust modes:**
- `"blackEq"` -- Edge-based black equalization (normalizes ink darkness)
- `"histogram"` -- Cumulative histogram matching (first frame = reference)
- `"histoL"` -- Line-width distribution matching

**Note:** When processing a level with `processLevel()`, the first frame becomes the reference for auto-adjust algorithms. Subsequent frames are matched to the first frame's tonal distribution.

---

## Tracker

Track object movement across frames using Variable Mean-Shift algorithm with Interpolated Template Matching.

```javascript
var tracker = new Tracker();

// Configuration
tracker.threshold = 0.2;        // 0-1: confidence threshold to mark object as lost (default 0.2)
tracker.sensitivity = 0.01;     // 0-1: template matching acceptance threshold (default 0.01)
tracker.variableRegion = false; // adaptive tracking box size
tracker.includeBackground = false; // background-aware tracking

// Define tracking regions (x, y, width, height in pixel coordinates)
// Returns region index
var regionIdx = tracker.addRegion(100, 50, 40, 40);  // Track a 40x40 region at (100,50)
tracker.addRegion(200, 80, 30, 30);                   // Track a second region

// Track across frames in a level
// Returns array of per-region results
var results = tracker.track(level, 1, 24);  // track from frame 1 to 24

// Access results
for (var i = 0; i < results.length; i++) {
    var region = results[i];
    print("Region " + i + ":");
    for (var f = 0; f < region.x.length; f++) {
        print("  frame " + f + ": x=" + region.x[f] + " y=" + region.y[f]
              + " status=" + region.status[f]);
    }
}
```

**Result structure:** Array of objects, one per tracked region:
```javascript
[{
    x: [x0, x1, x2, ...],         // X position per frame
    y: [y0, y1, y2, ...],         // Y position per frame
    status: ["VISIBLE", "VISIBLE", "WARNING", ...]  // Tracking status per frame
}, ...]
```

**Status values:** `"VISIBLE"` (good track), `"WARNING"` (uncertain), `"INVISIBLE"` (lost)

**Applying results to keyframes:**
```javascript
// Track object motion
var results = tracker.track(level, 1, 24);

// Apply tracked X/Y to a stage object
var obj = scene.getStageObject(0);
for (var f = 0; f < results[0].x.length; f++) {
    obj.setKeyframe(f, "x", results[0].x[f]);
    obj.setKeyframe(f, "y", results[0].y[f]);
}
```

---

### CenterlineVectorizer

Convert raster images to vector by extracting the medial axis skeleton of brushstrokes. Output strokes have variable thickness encoding the original stroke width.

```javascript
var cv = new CenterlineVectorizer();

// Configuration (all optional, defaults shown)
cv.threshold = 8;              // 0-8: ink/paper distinction
cv.accuracy = 7;               // 1-10: fidelity vs. simplicity
cv.despeckling = 5;             // 0-100: noise removal (min region area)
cv.maxThickness = 200;          // 0-200+: max stroke thickness (0 = outline only)
cv.thicknessCalibration = 100;  // 0-200: post-processing thickness scale (%)
cv.preservePaintedAreas = true; // compute fill regions
cv.addBorder = false;           // add transparent frame border
cv.eir = false;                 // enhanced ink recognition for full-color sources

// Vectorize a single image (returns vector Image)
var vectorImg = cv.vectorize(rasterImage);

// Vectorize an entire level (returns Level with all frames vectorized)
var vectorLevel = cv.vectorize(rasterLevel);
```

**Input:** Raster or ToonzRaster Image/Level
**Output:** Vector Image/Level

---

### OutlineVectorizer

Convert raster images to vector by tracing contour boundaries. Output strokes are uniform-thickness outlines.

```javascript
var ov = new OutlineVectorizer();

// Configuration (all optional, defaults shown)
ov.accuracy = 7;               // 0-10: curve simplification vs. fidelity
ov.despeckling = 4;             // 0-200+: edge despeckling (pixels)
ov.preservePaintedAreas = true; // compute fill regions
ov.cornerAdherence = 50;       // 0-100: contour corner following
ov.cornerAngle = 45;           // 0-180: angle-based corner detection (degrees)
ov.cornerCurveRadius = 25;     // 0-100: curvature-based corner detection
ov.maxColors = 50;             // 1-256: color quantization limit (fullcolor input)
ov.transparentColor = "#ffffff"; // color recognized as transparent
ov.toneThreshold = 128;        // 0-255: tone threshold for TLV input

// Vectorize a single image (returns vector Image)
var vectorImg = ov.vectorize(rasterImage);

// Vectorize an entire level (returns Level with all frames vectorized)
var vectorLevel = ov.vectorize(rasterLevel);
```

**Input:** Raster or ToonzRaster Image/Level
**Output:** Vector Image/Level

---

### Vectorization Example

```javascript
// Create a raster drawing to vectorize
var rc = new RasterCanvas(256, 256);
var pal = new Palette();
var ink = pal.addColor(0, 0, 0, 255);
rc.setPalette(pal);
rc.brushStroke([[60,128,4],[128,200,4],[196,128,4]], ink, true);
rc.brushStroke([[128,200,4],[128,60,4]], ink, true);
var rasterImg = rc.toImage();

// Centerline vectorization
var cv = new CenterlineVectorizer();
cv.accuracy = 9;
cv.maxThickness = 100;
var vectorImg = cv.vectorize(rasterImg);
vectorImg.save("/tmp/vectorized_centerline.pli");

// Outline vectorization
var ov = new OutlineVectorizer();
ov.accuracy = 8;
ov.cornerAngle = 60;
var vectorImg2 = ov.vectorize(rasterImg);
vectorImg2.save("/tmp/vectorized_outline.pli");
```

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
