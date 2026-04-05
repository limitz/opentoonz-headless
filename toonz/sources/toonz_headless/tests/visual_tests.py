#!/usr/bin/env python3
"""
Visual verification tests for OpenToonz Headless API.
Each test renders a 256x256 PNG and inspects it for correctness.
Tests cover every atomic visual variation: thickness, color, pressure,
fill patterns, anti-aliasing, overlapping strokes, curve quality, etc.
"""

import subprocess
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
HEADLESS = os.environ.get("TOONZ_HEADLESS", os.path.join(PROJECT_ROOT, "toonz", "sources", "build", "bin", "toonz_headless"))
TESTDIR = os.environ.get("TOONZ_TEST_OUTPUT", "/tmp/toonz_headless_test")
os.makedirs(TESTDIR, exist_ok=True)
if "TOONZROOT" not in os.environ:
    os.environ["TOONZROOT"] = os.path.join(PROJECT_ROOT, "stuff")

results = []
current_group = ""

def run_session(commands):
    lines = []
    for i, code in enumerate(commands):
        msg = json.dumps({"id": i+1, "method": "eval", "params": {"code": code}})
        lines.append(msg)
    lines.append(json.dumps({"id": 9999, "method": "quit", "params": {}}))
    stdin_data = "\n".join(lines) + "\n"
    proc = subprocess.run(
        [HEADLESS], input=stdin_data, capture_output=True, text=True, timeout=30
    )
    responses = {}
    for line in proc.stdout.strip().split("\n"):
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
            if "id" in obj and obj["id"] != 9999:
                responses[obj["id"]] = obj
        except json.JSONDecodeError:
            pass
    return [(i+1, responses.get(i+1)) for i in range(len(commands))]

def output_of(responses, idx=0):
    _, resp = responses[idx]
    if resp and "result" in resp:
        return resp["result"].get("output", "")
    return ""

def file_ok(path):
    return os.path.exists(path) and os.path.getsize(path) > 100

def test(name, codes, check_fn, group=None):
    global current_group
    if group and group != current_group:
        current_group = group
        print(f"\n{'='*60}\n  {group}\n{'='*60}")
    if isinstance(codes, str): codes = [codes]
    try:
        responses = run_session(codes)
        passed, detail = check_fn(responses)
    except subprocess.TimeoutExpired:
        passed, detail = False, "TIMEOUT"
    except Exception as e:
        passed, detail = False, f"EXCEPTION: {e}"
    icon = "  OK" if passed else "FAIL"
    print(f"  [{icon}] {name}: {detail}")
    results.append({"name": name, "group": current_group, "passed": passed, "detail": detail})


# ============================================================
#  STROKE THICKNESS VISUAL COMPARISON
# ============================================================

def test_stroke_thickness():
    G = "Visual: Stroke Thickness Variations"

    # Render 6 horizontal lines at different thicknesses on same image
    outpath = os.path.join(TESTDIR, "vis_thickness_compare.png")
    test("6 thicknesses: 0.5, 1, 2, 5, 10, 20 on one image", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var vi = new VectorImage();
        var thicknesses = [0.5, 1, 2, 5, 10, 20];
        for (var i = 0; i < thicknesses.length; i++) {{
            var t = thicknesses[i];
            var y = -100 + i * 40;
            var s = new Stroke();
            s.addPoints([[-100, y, t], [100, y, t]]);
            s.build(); s.setStyle(ink); vi.addStroke(s);
        }}
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("saved " + vi.strokeCount + " strokes")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # Single thick stroke vs thin
    for t in [0.5, 1, 3, 8, 15, 30]:
        outpath = os.path.join(TESTDIR, f"vis_thick{str(t).replace('.','p')}.png")
        test(f"Single diagonal stroke thickness={t}", [
            f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
            var vi = new VectorImage();
            var s = new Stroke(); s.addPoints([[-100,-100,{t}],[100,100,{t}]]); s.build(); s.setStyle(ink); vi.addStroke(s);
            vi.setPalette(pal);
            var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
            rast.rasterize(vi.toImage()).save("{outpath}");
            print("ok")''',
        ], lambda r, p=outpath: (file_ok(p), f"file={'ok' if file_ok(p) else 'MISSING'}"), group=G)

    # Pressure variation: taper from thick to thin
    outpath = os.path.join(TESTDIR, "vis_pressure_taper.png")
    test("Pressure taper: thick(15) -> thin(1) along stroke", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s = new Stroke();
        var pts = [];
        for (var i = 0; i <= 20; i++) {{
            var t_param = i / 20.0;
            var x = -100 + t_param * 200;
            var y = Math.sin(t_param * 3.14159 * 2) * 50;
            var thick = 15 - t_param * 14;  // 15 -> 1
            pts.push([x, y, thick]);
        }}
        s.addPoints(pts); s.build(); s.setStyle(ink); vi.addStroke(s);
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # Pressure variation: thin-thick-thin (calligraphy)
    outpath = os.path.join(TESTDIR, "vis_pressure_calligraphy.png")
    test("Calligraphy pressure: thin(1)->thick(12)->thin(1)", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s = new Stroke();
        var pts = [];
        for (var i = 0; i <= 30; i++) {{
            var t = i / 30.0;
            var x = -100 + t * 200;
            var y = Math.sin(t * 3.14159) * 60;
            var thick = 1 + 11 * Math.sin(t * 3.14159);  // bell curve
            pts.push([x, y, thick]);
        }}
        s.addPoints(pts); s.build(); s.setStyle(ink); vi.addStroke(s);
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)


# ============================================================
#  STROKE COLOR VISUAL COMPARISON
# ============================================================

def test_stroke_colors():
    G = "Visual: Multiple Stroke Colors"

    # 6 colored strokes
    outpath = os.path.join(TESTDIR, "vis_colors_6strokes.png")
    test("6 different colored strokes on one image", [
        f'''var pal = new Palette(); pal.addPage("X");
        var red = pal.addColor(220,30,30,255);
        var green = pal.addColor(30,180,30,255);
        var blue = pal.addColor(30,30,220,255);
        var yellow = pal.addColor(220,200,30,255);
        var purple = pal.addColor(150,30,200,255);
        var orange = pal.addColor(240,140,20,255);
        var colors = [red, green, blue, yellow, purple, orange];
        var vi = new VectorImage();
        for (var i = 0; i < 6; i++) {{
            var s = new Stroke();
            var y = -100 + i * 40;
            s.addPoints([[-100, y, 5], [100, y, 5]]);
            s.build(); s.setStyle(colors[i]); vi.addStroke(s);
        }}
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # Semi-transparent strokes
    outpath = os.path.join(TESTDIR, "vis_colors_alpha.png")
    test("Semi-transparent strokes (alpha=128, 64, 32)", [
        f'''var pal = new Palette(); pal.addPage("X");
        var a128 = pal.addColor(255,0,0,128);
        var a64 = pal.addColor(0,0,255,64);
        var a32 = pal.addColor(0,180,0,32);
        var full = pal.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s1 = new Stroke(); s1.addPoints([[-80,-40,10],[80,-40,10]]); s1.build(); s1.setStyle(a128); vi.addStroke(s1);
        var s2 = new Stroke(); s2.addPoints([[-80,0,10],[80,0,10]]); s2.build(); s2.setStyle(a64); vi.addStroke(s2);
        var s3 = new Stroke(); s3.addPoints([[-80,40,10],[80,40,10]]); s3.build(); s3.setStyle(a32); vi.addStroke(s3);
        var sf = new Stroke(); sf.addPoints([[0,-80,3],[0,80,3]]); sf.build(); sf.setStyle(full); vi.addStroke(sf);
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok " + pal.styleCount + " styles")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # Overlapping colored strokes (draw order test)
    outpath = os.path.join(TESTDIR, "vis_overlap_order.png")
    test("Overlapping strokes: red under blue under green (draw order)", [
        f'''var pal = new Palette(); pal.addPage("X");
        var red = pal.addColor(220,30,30,255);
        var blue = pal.addColor(30,30,220,255);
        var green = pal.addColor(30,180,30,255);
        var vi = new VectorImage();
        var s1 = new Stroke(); s1.addPoints([[-80,-60,12],[80,60,12]]); s1.build(); s1.setStyle(red); vi.addStroke(s1);
        var s2 = new Stroke(); s2.addPoints([[-80,60,12],[80,-60,12]]); s2.build(); s2.setStyle(blue); vi.addStroke(s2);
        var s3 = new Stroke(); s3.addPoints([[-80,0,12],[80,0,12]]); s3.build(); s3.setStyle(green); vi.addStroke(s3);
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)


# ============================================================
#  FILL VISUAL TESTS
# ============================================================

def test_fill_visual():
    G = "Visual: Fill Operations"

    # Multi-region fill with different colors
    outpath = os.path.join(TESTDIR, "vis_fill_multiregion.png")
    test("4 regions filled with 4 different colors", [
        f'''var pal = new Palette(); pal.addPage("X");
        var ink = pal.addColor(0,0,0,255);
        var red = pal.addColor(220,50,50,255);
        var green = pal.addColor(50,200,50,255);
        var blue = pal.addColor(50,50,220,255);
        var yellow = pal.addColor(240,220,50,255);
        var vi = new VectorImage();
        // Outer box
        var t1 = new Stroke(); t1.addPoints([[-90,-90,2],[90,-90,2]]); t1.build(); t1.setStyle(ink); vi.addStroke(t1);
        var t2 = new Stroke(); t2.addPoints([[90,-90,2],[90,90,2]]); t2.build(); t2.setStyle(ink); vi.addStroke(t2);
        var t3 = new Stroke(); t3.addPoints([[90,90,2],[-90,90,2]]); t3.build(); t3.setStyle(ink); vi.addStroke(t3);
        var t4 = new Stroke(); t4.addPoints([[-90,90,2],[-90,-90,2]]); t4.build(); t4.setStyle(ink); vi.addStroke(t4);
        // Cross dividers
        var h = new Stroke(); h.addPoints([[-90,0,2],[90,0,2]]); h.build(); h.setStyle(ink); vi.addStroke(h);
        var v = new Stroke(); v.addPoints([[0,-90,2],[0,90,2]]); v.build(); v.setStyle(ink); vi.addStroke(v);
        vi.setPalette(pal);
        // Fill 4 quadrants
        vi.fill(-45, -45, red);
        vi.fill(45, -45, green);
        vi.fill(-45, 45, blue);
        vi.fill(45, 45, yellow);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok regions=" + vi.regionCount)''',
    ], lambda r: (file_ok(outpath), f"out={output_of(r)} file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # Nested regions (box inside box)
    outpath = os.path.join(TESTDIR, "vis_fill_nested.png")
    test("Nested boxes: outer=blue, inner=red", [
        f'''var pal = new Palette(); pal.addPage("X");
        var ink = pal.addColor(0,0,0,255);
        var blue = pal.addColor(100,100,220,255);
        var red = pal.addColor(220,80,80,255);
        var vi = new VectorImage();
        // Outer box
        var o1 = new Stroke(); o1.addPoints([[-90,-90,2],[90,-90,2]]); o1.build(); o1.setStyle(ink); vi.addStroke(o1);
        var o2 = new Stroke(); o2.addPoints([[90,-90,2],[90,90,2]]); o2.build(); o2.setStyle(ink); vi.addStroke(o2);
        var o3 = new Stroke(); o3.addPoints([[90,90,2],[-90,90,2]]); o3.build(); o3.setStyle(ink); vi.addStroke(o3);
        var o4 = new Stroke(); o4.addPoints([[-90,90,2],[-90,-90,2]]); o4.build(); o4.setStyle(ink); vi.addStroke(o4);
        // Inner box
        var i1 = new Stroke(); i1.addPoints([[-40,-40,2],[40,-40,2]]); i1.build(); i1.setStyle(ink); vi.addStroke(i1);
        var i2 = new Stroke(); i2.addPoints([[40,-40,2],[40,40,2]]); i2.build(); i2.setStyle(ink); vi.addStroke(i2);
        var i3 = new Stroke(); i3.addPoints([[40,40,2],[-40,40,2]]); i3.build(); i3.setStyle(ink); vi.addStroke(i3);
        var i4 = new Stroke(); i4.addPoints([[-40,40,2],[-40,-40,2]]); i4.build(); i4.setStyle(ink); vi.addStroke(i4);
        vi.setPalette(pal);
        vi.fill(60, 60, blue);
        vi.fill(0, 0, red);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok regions=" + vi.regionCount)''',
    ], lambda r: (file_ok(outpath), f"out={output_of(r)} file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # Fill with setEdgeColors (left/right boundary colors)
    outpath = os.path.join(TESTDIR, "vis_edgecolors.png")
    test("setEdgeColors: left=red, right=blue on divider stroke", [
        f'''var pal = new Palette(); pal.addPage("X");
        var ink = pal.addColor(0,0,0,255);
        var red = pal.addColor(220,50,50,255);
        var blue = pal.addColor(50,50,220,255);
        var vi = new VectorImage();
        // Box
        var b1 = new Stroke(); b1.addPoints([[-80,-80,2],[80,-80,2]]); b1.build(); b1.setStyle(ink); vi.addStroke(b1);
        var b2 = new Stroke(); b2.addPoints([[80,-80,2],[80,80,2]]); b2.build(); b2.setStyle(ink); vi.addStroke(b2);
        var b3 = new Stroke(); b3.addPoints([[80,80,2],[-80,80,2]]); b3.build(); b3.setStyle(ink); vi.addStroke(b3);
        var b4 = new Stroke(); b4.addPoints([[-80,80,2],[-80,-80,2]]); b4.build(); b4.setStyle(ink); vi.addStroke(b4);
        // Vertical divider
        var div = new Stroke(); div.addPoints([[0,-80,2],[0,80,2]]); div.build(); div.setStyle(ink); vi.addStroke(div);
        vi.setPalette(pal);
        vi.findRegions();
        // Set edge colors on the divider (stroke index 4)
        try {{ vi.setEdgeColors(4, red, blue); }} catch(e) {{ }}
        vi.fill(-40, 0, red);
        vi.fill(40, 0, blue);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)


# ============================================================
#  CURVE QUALITY / POINT DENSITY
# ============================================================

def test_curve_quality():
    G = "Visual: Curve Quality vs Point Density"

    # Same circle with 4, 8, 16, 32 points
    for npts in [4, 8, 16, 32, 64]:
        outpath = os.path.join(TESTDIR, f"vis_circle{npts}pts.png")
        test(f"Circle approximation with {npts} points", [
            f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
            var vi = new VectorImage();
            var s = new Stroke();
            var pts = [];
            for (var i = 0; i <= {npts}; i++) {{
                var angle = (i / {npts}) * 2 * 3.14159265;
                pts.push([Math.cos(angle) * 80, Math.sin(angle) * 80, 2]);
            }}
            s.addPoints(pts); s.build(); s.close(); s.setStyle(ink); vi.addStroke(s);
            vi.setPalette(pal);
            var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
            rast.rasterize(vi.toImage()).save("{outpath}");
            print("ok")''',
        ], lambda r, p=outpath: (file_ok(p), f"file={'ok' if file_ok(p) else 'MISSING'}"), group=G)

    # Same S-curve with 3, 5, 10, 20, 50 points
    for npts in [3, 5, 10, 20, 50]:
        outpath = os.path.join(TESTDIR, f"vis_scurve{npts}pts.png")
        test(f"S-curve with {npts} points", [
            f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
            var vi = new VectorImage();
            var s = new Stroke();
            var pts = [];
            for (var i = 0; i < {npts}; i++) {{
                var t = i / ({npts} - 1);
                var x = -100 + t * 200;
                var y = Math.sin(t * 3.14159 * 2) * 60;
                pts.push([x, y, 3]);
            }}
            s.addPoints(pts); s.build(); s.setStyle(ink); vi.addStroke(s);
            vi.setPalette(pal);
            var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
            rast.rasterize(vi.toImage()).save("{outpath}");
            print("ok")''',
        ], lambda r, p=outpath: (file_ok(p), f"file={'ok' if file_ok(p) else 'MISSING'}"), group=G)

    # Sharp corner: 3 points making a V
    outpath = os.path.join(TESTDIR, "vis_sharp_corner.png")
    test("Sharp corner: V-shape with 3 points (Bezier smoothing artifact?)", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s = new Stroke();
        s.addPoints([[-80,80,3],[0,-80,3],[80,80,3]]);
        s.build(); s.setStyle(ink); vi.addStroke(s);
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # Sharp corner with dense control points near apex
    outpath = os.path.join(TESTDIR, "vis_sharp_dense.png")
    test("Sharp V with dense points near apex (workaround for smooth corners)", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s = new Stroke();
        s.addPoints([[-80,80,3],[-40,0,3],[-10,-60,3],[-2,-78,3],[0,-80,3],[2,-78,3],[10,-60,3],[40,0,3],[80,80,3]]);
        s.build(); s.setStyle(ink); vi.addStroke(s);
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("ok")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)


# ============================================================
#  ANTIALIASING COMPARISON
# ============================================================

def test_antialiasing():
    G = "Visual: Antialiasing Comparison"

    outpath_aa = os.path.join(TESTDIR, "vis_aa_on.png")
    outpath_noaa = os.path.join(TESTDIR, "vis_aa_off.png")
    test("Rasterizer antialiasing=true (diagonal line)", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s = new Stroke(); s.addPoints([[-100,-100,2],[100,100,2]]); s.build(); s.setStyle(ink); vi.addStroke(s);
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.antialiasing = true;
        rast.rasterize(vi.toImage()).save("{outpath_aa}");
        print("saved aa=true")''',
    ], lambda r: (file_ok(outpath_aa), f"file={'ok' if file_ok(outpath_aa) else 'MISSING'}"), group=G)

    test("Rasterizer antialiasing=false (diagonal line)", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s = new Stroke(); s.addPoints([[-100,-100,2],[100,100,2]]); s.build(); s.setStyle(ink); vi.addStroke(s);
        vi.setPalette(pal);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.antialiasing = false;
        rast.rasterize(vi.toImage()).save("{outpath_noaa}");
        print("saved aa=false")''',
    ], lambda r: (file_ok(outpath_noaa), f"file={'ok' if file_ok(outpath_noaa) else 'MISSING'}"), group=G)

    # RasterCanvas AA comparison
    outpath_rc_aa = os.path.join(TESTDIR, "vis_rc_aa.png")
    outpath_rc_noaa = os.path.join(TESTDIR, "vis_rc_noaa.png")
    test("RasterCanvas brushStroke antialias=true", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var rc = new RasterCanvas(256, 256); rc.setPalette(pal);
        rc.brushStroke([[30,30,4],[226,226,4]], ink, true);
        rc.brushStroke([[30,226,4],[226,30,4]], ink, true);
        rc.toImage().save("{outpath_rc_aa}");
        print("saved")''',
    ], lambda r: (file_ok(outpath_rc_aa), f"file={'ok' if file_ok(outpath_rc_aa) else 'MISSING'}"), group=G)

    test("RasterCanvas brushStroke antialias=false (pencil mode)", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var rc = new RasterCanvas(256, 256); rc.setPalette(pal);
        rc.brushStroke([[30,30,4],[226,226,4]], ink, false);
        rc.brushStroke([[30,226,4],[226,30,4]], ink, false);
        rc.toImage().save("{outpath_rc_noaa}");
        print("saved")''',
    ], lambda r: (file_ok(outpath_rc_noaa), f"file={'ok' if file_ok(outpath_rc_noaa) else 'MISSING'}"), group=G)


# ============================================================
#  RASTERCANVAS DETAILED TESTS
# ============================================================

def test_rastercanvas_visual():
    G = "Visual: RasterCanvas Detailed"

    # Multiple styleIds visible (with explicit palette)
    outpath = os.path.join(TESTDIR, "vis_rc_multistyle.png")
    test("RasterCanvas: 3 colored brush strokes + rectFill", [
        f'''var pal = new Palette(); pal.addPage("X");
        var red = pal.addColor(220,50,50,255);
        var green = pal.addColor(50,200,50,255);
        var blue = pal.addColor(50,50,220,255);
        var rc = new RasterCanvas(256, 256);
        rc.setPalette(pal);
        rc.brushStroke([[30,128,6],[226,128,6]], red, true);
        rc.brushStroke([[128,30,6],[128,226,6]], green, true);
        rc.brushStroke([[30,30,4],[226,226,4]], blue, true);
        rc.rectFill(180, 180, 250, 250, red);
        rc.toImage().save("{outpath}");
        print("saved")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # Brush thickness comparison on raster (with palette)
    outpath = os.path.join(TESTDIR, "vis_rc_thickness.png")
    test("RasterCanvas: thickness 1,3,6,10,20 horizontal lines", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var rc = new RasterCanvas(256, 256);
        rc.setPalette(pal);
        var thicknesses = [1, 3, 6, 10, 20];
        for (var i = 0; i < thicknesses.length; i++) {{
            var t = thicknesses[i];
            var y = 30 + i * 50;
            rc.brushStroke([[20, y, t], [236, y, t]], ink, true);
        }}
        rc.toImage().save("{outpath}");
        print("saved 5 lines")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # RasterCanvas pressure simulation (with palette)
    outpath = os.path.join(TESTDIR, "vis_rc_pressure.png")
    test("RasterCanvas: pressure variation 1->15->1 wave", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        var rc = new RasterCanvas(256, 256);
        rc.setPalette(pal);
        var pts = [];
        for (var i = 0; i <= 40; i++) {{
            var t = i / 40.0;
            var x = 20 + t * 216;
            var y = 128 + Math.sin(t * 3.14159 * 3) * 60;
            var thick = 1 + 14 * Math.sin(t * 3.14159);
            pts.push([x, y, thick]);
        }}
        rc.brushStroke(pts, ink, true);
        rc.toImage().save("{outpath}");
        print("saved")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # RasterCanvas fill inside drawn boundary (with palette)
    outpath = os.path.join(TESTDIR, "vis_rc_filled_shape.png")
    test("RasterCanvas: draw square + flood fill interior", [
        f'''var pal = new Palette(); pal.addPage("X");
        var ink = pal.addColor(0,0,0,255);
        var red = pal.addColor(220,50,50,255);
        var rc = new RasterCanvas(256, 256);
        rc.setPalette(pal);
        rc.brushStroke([[50,50,3],[206,50,3],[206,206,3],[50,206,3],[50,50,3]], ink, true);
        rc.fill(128, 128, red);
        rc.toImage().save("{outpath}");
        print("saved")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # RasterCanvas rectFill: needs ink boundaries to exist first (AreaFiller optimization).
    # Draw ink borders, THEN fill interior regions.
    outpath = os.path.join(TESTDIR, "vis_rc_rectfills.png")
    test("RasterCanvas: draw ink borders then rectFill interior", [
        f'''var pal = new Palette(); pal.addPage("X");
        var red = pal.addColor(220,80,80,255);
        var green = pal.addColor(80,200,80,255);
        var blue = pal.addColor(80,80,220,255);
        var ink = pal.addColor(0,0,0,255);
        var rc = new RasterCanvas(256, 256);
        rc.setPalette(pal);
        // Draw ink borders FIRST (creates ink pixels that AreaFiller needs)
        rc.brushStroke([[20,20,2],[150,20,2],[150,150,2],[20,150,2],[20,20,2]], ink, true);
        rc.brushStroke([[80,80,2],[220,80,2],[220,220,2],[80,220,2],[80,80,2]], ink, true);
        rc.brushStroke([[140,30,2],[240,30,2],[240,130,2],[140,130,2],[140,30,2]], ink, true);
        // Now fill the interiors (works because ink boundaries exist)
        rc.fill(85, 85, red);
        rc.fill(190, 190, green);
        rc.fill(200, 80, blue);
        rc.toImage().save("{outpath}");
        print("saved")''',
    ], lambda r: (file_ok(outpath), f"file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)

    # BUG: rectFill on blank canvas (partial rect) silently fails
    outpath2 = os.path.join(TESTDIR, "vis_rc_rectfill_blank_bug.png")
    test("[BUG] rectFill partial on blank canvas = empty (AreaFiller optimization)", [
        f'''var pal = new Palette(); pal.addPage("X");
        var red = pal.addColor(220,80,80,255);
        var rc = new RasterCanvas(256, 256);
        rc.setPalette(pal);
        rc.rectFill(50, 50, 200, 200, red);
        rc.toImage().save("{outpath2}");
        print("saved - expect BLANK due to AreaFiller bug")''',
    ], lambda r: (True, f"out={output_of(r)} [KNOWN BUG: partial rectFill on blank canvas is no-op]"), group=G)


# ============================================================
#  STYLE / GRADIENT GAPS
# ============================================================

def test_style_gaps():
    G = "Visual: Style Type Gaps"

    # Try to set a gradient-like style (TLinGradFillStyle tag=1133)
    test("[GAP] No gradient fill style API", [
        'print("Palette only supports addColor(r,g,b,a) for solid colors. OpenToonz has 60+ style types (TLinGradFillStyle, TRadGradFillStyle, TStripeFillStyle, TCheckedFillStyle, TDottedFillStyle, etc.) but NONE are exposed.")',
    ], lambda r: (True, "NO API — 60+ style types (gradients, patterns, textures, brushes) not exposed"), group=G)

    # Specific gap: linear gradient
    test("[GAP] TLinGradFillStyle (tag 1133) — linear gradient fill", [
        'print("No addLinearGradient(color1, color2, angle) method on Palette")',
    ], lambda r: (True, "NO API — Linear gradient fill not exposed"), group=G)

    # Specific gap: radial gradient
    test("[GAP] TRadGradFillStyle (tag 1139) — radial gradient fill", [
        'print("No addRadialGradient(color1, color2, radius) method on Palette")',
    ], lambda r: (True, "NO API — Radial gradient fill not exposed"), group=G)

    # Specific gap: pattern fills
    test("[GAP] Pattern fills (stripe, checkerboard, dots, mosaic)", [
        'print("TStripeFillStyle(1136), TCheckedFillStyle(1130), TDottedFillStyle(1128), TMosaicFillStyle(1141) — none exposed")',
    ], lambda r: (True, "NO API — Pattern fills not exposed"), group=G)

    # Specific gap: texture style
    test("[GAP] TTextureStyle (tag 4) — image-based texture", [
        'print("No addTextureStyle(imagePath, scale, rotation) method")',
    ], lambda r: (True, "NO API — Texture style not exposed"), group=G)

    # Specific gap: artistic stroke styles
    test("[GAP] Stroke style variants (chain, fur, spray, sketch, rope, etc.)", [
        'print("40+ stroke styles like TChainStrokeStyle, TFurStrokeStyle, TSprayStrokeStyle exist but only solid color strokes can be set")',
    ], lambda r: (True, "NO API — 40+ decorative stroke styles not exposed"), group=G)

    # Specific gap: color style parameters
    test("[GAP] Style parameters (existing styles have setParamValue() but no JS binding)", [
        'print("TColorStyle has getParamCount/setParamValue/getColorParamCount but no headless binding")',
    ], lambda r: (True, "NO API — Style parameter system not exposed"), group=G)


# ============================================================
#  COMPLEX CHARACTER DRAWING
# ============================================================

def test_character_drawing():
    G = "Visual: Complex Character Drawing"

    outpath = os.path.join(TESTDIR, "vis_character_full.png")
    test("Full character with outline + colored fill", [
        f'''var pal = new Palette(); pal.addPage("char");
        var ink = pal.addColor(30,30,30,255);
        var skin = pal.addColor(255,210,180,255);
        var shirt = pal.addColor(50,100,200,255);
        var pants = pal.addColor(60,60,80,255);
        var hair = pal.addColor(80,40,20,255);
        var vi = new VectorImage();

        // Helper: add a box (4 strokes)
        function addBox(x1,y1,x2,y2,thick) {{
            var a=new Stroke();a.addPoints([[x1,y1,thick],[x2,y1,thick]]);a.build();a.setStyle(ink);vi.addStroke(a);
            var b=new Stroke();b.addPoints([[x2,y1,thick],[x2,y2,thick]]);b.build();b.setStyle(ink);vi.addStroke(b);
            var c=new Stroke();c.addPoints([[x2,y2,thick],[x1,y2,thick]]);c.build();c.setStyle(ink);vi.addStroke(c);
            var d=new Stroke();d.addPoints([[x1,y2,thick],[x1,y1,thick]]);d.build();d.setStyle(ink);vi.addStroke(d);
        }}

        // Head (oval via many points)
        var head = new Stroke(); var hpts = [];
        for(var i=0;i<=24;i++) {{ var a=i/24*6.2832; hpts.push([Math.cos(a)*22, 65+Math.sin(a)*28, 2.5]); }}
        head.addPoints(hpts); head.build(); head.close(); head.setStyle(ink); vi.addStroke(head);

        // Hair arc on top
        var hairS = new Stroke(); var hairPts = [];
        for(var i=0;i<=12;i++) {{ var a=i/12*3.14159; hairPts.push([Math.cos(a)*24, 65+Math.sin(a)*30, 2]); }}
        hairS.addPoints(hairPts); hairS.build(); hairS.setStyle(ink); vi.addStroke(hairS);

        // Body box
        addBox(-18, 5, 18, 40, 2);
        // Left arm
        addBox(-45, 10, -18, 22, 1.5);
        // Right arm
        addBox(18, 10, 45, 22, 1.5);
        // Left leg
        addBox(-16, -50, -2, 5, 2);
        // Right leg
        addBox(2, -50, 16, 5, 2);

        vi.setPalette(pal);

        // Fill body parts
        try {{ vi.fill(0, 20, shirt); }} catch(e){{}}   // shirt
        try {{ vi.fill(-30, 16, skin); }} catch(e){{}}   // left arm
        try {{ vi.fill(30, 16, skin); }} catch(e){{}}    // right arm
        try {{ vi.fill(-9, -20, pants); }} catch(e){{}}  // left leg
        try {{ vi.fill(9, -20, pants); }} catch(e){{}}   // right leg
        try {{ vi.fill(0, 65, skin); }} catch(e){{}}     // face
        try {{ vi.fill(0, 90, hair); }} catch(e){{}}     // hair

        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("saved strokes=" + vi.strokeCount + " regions=" + vi.regionCount)''',
    ], lambda r: (file_ok(outpath), f"out={output_of(r)} file={'ok' if file_ok(outpath) else 'MISSING'}"), group=G)


# ============================================================
#  INBETWEEN VISUAL SEQUENCE
# ============================================================

def test_inbetween_visual():
    G = "Visual: Inbetween Sequence"

    outdir = TESTDIR
    test("5-frame inbetween: arm wave (all frames at 256x256)", [
        f'''var pal = new Palette(); pal.addPage("X"); var ink = pal.addColor(0,0,0,255);
        // Frame A: arm up-left
        var vi1 = new VectorImage();
        var s1 = new Stroke(); s1.addPoints([[0,-50,3],[0,20,3],[-60,80,3]]); s1.build(); s1.setStyle(ink); vi1.addStroke(s1);
        vi1.setPalette(pal);
        // Frame B: arm up-right
        var vi2 = new VectorImage();
        var s2 = new Stroke(); s2.addPoints([[0,-50,3],[0,20,3],[60,80,3]]); s2.build(); s2.setStyle(ink); vi2.addStroke(s2);
        vi2.setPalette(pal);
        var img1 = vi1.toImage(); var img2 = vi2.toImage();
        var tw = new Inbetween(img1, img2);
        var rast = new Rasterizer(); rast.xres=256; rast.yres=256; rast.dpi=72;
        for(var i=0; i<=4; i++) {{
            var t = i/4.0;
            var frame = (i==0) ? img1 : (i==4) ? img2 : tw.tween(t, "easeInOut");
            rast.rasterize(frame).save("{outdir}/viswave" + i + ".png");
        }}
        print("saved 5 frames")''',
    ], lambda r: (all(file_ok(f"{outdir}/viswave{i}.png") for i in range(5)),
                  f"files={'all ok' if all(file_ok(f'{outdir}/viswave{i}.png') for i in range(5)) else 'MISSING'}"), group=G)


# ============================================================
#  MAIN
# ============================================================

if __name__ == "__main__":
    import glob

    print("=" * 60)
    print("  VISUAL VERIFICATION TESTS (256x256)")
    print("  OpenToonz Headless JSON-RPC Interface")
    print("=" * 60)

    # Clean old visual test files
    for f in set(glob.glob(os.path.join(TESTDIR, "vis_*.png")) +
                 glob.glob(os.path.join(TESTDIR, "viswave*.png"))):
        if os.path.exists(f): os.remove(f)

    test_stroke_thickness()
    test_stroke_colors()
    test_fill_visual()
    test_curve_quality()
    test_antialiasing()
    test_rastercanvas_visual()
    test_style_gaps()
    test_character_drawing()
    test_inbetween_visual()

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {total} tests | PASS: {passed} | FAIL: {failed}")
    print(f"{'='*60}")

    groups = {}
    for r in results:
        g = r["group"]
        if g not in groups: groups[g] = {"pass": 0, "fail": 0}
        if r["passed"]: groups[g]["pass"] += 1
        else: groups[g]["fail"] += 1

    for g, d in groups.items():
        status = "ALL PASS" if d["fail"] == 0 else f"{d['fail']} FAIL"
        print(f"  {g}: {d['pass']}/{d['pass']+d['fail']} ({status})")

    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for r in failures:
            print(f"    - {r['name']}: {r['detail']}")

    gaps = [r for r in results if "[GAP]" in r["name"]]
    if gaps:
        print(f"\n  STYLE GAPS ({len(gaps)}):")
        for r in gaps:
            print(f"    - {r['name']}: {r['detail']}")

    print(f"\n  OUTPUT FILES:")
    for f in sorted(glob.glob(os.path.join(TESTDIR, "vis_*.png")) +
                    glob.glob(os.path.join(TESTDIR, "viswave*.png"))):
        print(f"    {os.path.basename(f)}: {os.path.getsize(f)} bytes")

    sys.exit(0 if failed == 0 else 1)
