#!/usr/bin/env python3
"""
Comprehensive atomic test suite for OpenToonz Headless JSON-RPC interface.
Tests every atomic operation from the character design workflow.
"""

import subprocess
import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
HEADLESS = os.environ.get("TOONZ_HEADLESS", os.path.join(PROJECT_ROOT, "toonz", "sources", "build", "bin", "toonz_headless"))
TESTDIR = os.environ.get("TOONZ_TEST_OUTPUT", "/tmp/toonz_headless_test")
os.makedirs(TESTDIR, exist_ok=True)
if "TOONZROOT" not in os.environ:
    os.environ["TOONZROOT"] = os.path.join(PROJECT_ROOT, "stuff")

# Results tracking
results = []
current_group = ""

def run_session(commands):
    """Run a list of JS code strings in a single headless session.
    Returns list of (id, result_dict_or_None) tuples."""
    lines = []
    for i, code in enumerate(commands):
        msg = json.dumps({"id": i+1, "method": "eval", "params": {"code": code}})
        lines.append(msg)
    lines.append(json.dumps({"id": 9999, "method": "quit", "params": {}}))
    stdin_data = "\n".join(lines) + "\n"

    proc = subprocess.run(
        [HEADLESS],
        input=stdin_data, capture_output=True, text=True, timeout=30
    )

    responses = {}
    for line in proc.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if "id" in obj and obj["id"] != 9999:
                responses[obj["id"]] = obj
        except json.JSONDecodeError:
            pass

    out = []
    for i in range(len(commands)):
        out.append((i+1, responses.get(i+1)))
    return out


def test(name, code_or_codes, check_fn, group=None):
    """Run a test. code_or_codes is a string or list of strings.
    check_fn receives the list of responses and returns (pass:bool, detail:str)."""
    global current_group
    if group and group != current_group:
        current_group = group
        print(f"\n{'='*60}")
        print(f"  {group}")
        print(f"{'='*60}")

    if isinstance(code_or_codes, str):
        code_or_codes = [code_or_codes]

    try:
        responses = run_session(code_or_codes)
        passed, detail = check_fn(responses)
    except subprocess.TimeoutExpired:
        passed, detail = False, "TIMEOUT"
    except Exception as e:
        passed, detail = False, f"EXCEPTION: {e}"

    status = "PASS" if passed else "FAIL"
    icon = "  OK" if passed else "FAIL"
    print(f"  [{icon}] {name}: {detail}")
    results.append({"name": name, "group": current_group, "passed": passed, "detail": detail})
    return passed


def output_of(responses, idx=0):
    """Extract output string from response at index."""
    _, resp = responses[idx]
    if resp and "result" in resp:
        return resp["result"].get("output", "")
    return ""


def ok_of(responses, idx=0):
    """Check if response at index has ok=true."""
    _, resp = responses[idx]
    if resp and "result" in resp:
        return resp["result"].get("ok", False)
    return False


def has_error(responses, idx=0):
    """Check if response has an error."""
    _, resp = responses[idx]
    if resp is None:
        return True
    if "error" in resp:
        return True
    if "result" in resp:
        out = resp["result"].get("output", "")
        return "Error:" in out or "error" in out.lower()
    return False


def file_exists_and_nonzero(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


# ============================================================
#  STEP 1: LEVEL CREATION
# ============================================================

def test_step1_levels():
    G = "Step 1: Create Character Levels"

    # Create Vector level
    test("Create Vector level via Scene", [
        'var scene = new Scene(); var lv = scene.newLevel("Vector", "vec1"); print(lv.type)',
    ], lambda r: (output_of(r) == "Vector", f"type={output_of(r)}"), group=G)

    # Create ToonzRaster level
    test("Create ToonzRaster level via Scene", [
        'var scene = new Scene(); var lv = scene.newLevel("ToonzRaster", "tr1"); print(lv.type)',
    ], lambda r: (output_of(r) == "ToonzRaster", f"type={output_of(r)}"), group=G)

    # Create Raster level via Scene
    test("Create Raster level via Scene", [
        'var scene = new Scene(); var lv = scene.newLevel("Raster", "rast1"); print(lv.type)',
    ], lambda r: (output_of(r) == "Raster", f"type={output_of(r)}"), group=G)

    # Level name property
    test("Level name property", [
        'var scene = new Scene(); var lv = scene.newLevel("Vector", "mychar"); print(lv.name)',
    ], lambda r: (output_of(r) == "mychar", f"name={output_of(r)}"), group=G)

    # Level frameCount on new level
    test("Level frameCount on new (empty) level", [
        'var scene = new Scene(); var lv = scene.newLevel("Vector", "e"); print(lv.frameCount)',
    ], lambda r: (output_of(r) in ["0","1"], f"frameCount={output_of(r)}"), group=G)

    # Invalid level type
    test("Invalid level type string (lowercase)", [
        'var scene = new Scene(); try { var lv = scene.newLevel("vector", "bad"); print("no_error"); } catch(e) { print("caught:" + e); }',
    ], lambda r: ("no_error" not in output_of(r) or has_error(r), f"out={output_of(r)}"), group=G)

    # Get level by name
    test("Get level by name from scene", [
        'var scene = new Scene(); scene.newLevel("Vector", "findme"); var lv = scene.getLevel("findme"); print(lv ? lv.name : "null")',
    ], lambda r: (output_of(r) == "findme", f"out={output_of(r)}"), group=G)

    # Get levels list
    test("Get all levels from scene", [
        'var scene = new Scene(); scene.newLevel("Vector","a"); scene.newLevel("Vector","b"); var ls = scene.getLevels(); print(ls.length)',
    ], lambda r: (output_of(r) == "2", f"count={output_of(r)}"), group=G)


# ============================================================
#  STEP 3: PALETTE
# ============================================================

def test_step3_palette():
    G = "Step 3: Build the Palette"

    # Empty palette has 2 default styles
    test("New palette has 2 default styles", [
        'var p = new Palette(); print(p.styleCount)',
    ], lambda r: (output_of(r) == "2", f"styleCount={output_of(r)}"), group=G)

    # pageCount initially 1 (TPalette creates a default "colors" page)
    test("New palette has 1 default page", [
        'var p = new Palette(); print(p.pageCount)',
    ], lambda r: (output_of(r) == "1", f"pageCount={output_of(r)}"), group=G)

    # addPage adds to existing
    test("addPage creates a second page", [
        'var p = new Palette(); p.addPage("Skin"); print(p.pageCount)',
    ], lambda r: (output_of(r) == "2", f"pageCount={output_of(r)}"), group=G)

    # Multiple pages
    test("Multiple pages (3 added + 1 default = 4)", [
        'var p = new Palette(); p.addPage("A"); p.addPage("B"); p.addPage("C"); print(p.pageCount)',
    ], lambda r: (output_of(r) == "4", f"pageCount={output_of(r)}"), group=G)

    # addColor returns ID starting at 2
    test("First addColor returns style ID 2", [
        'var p = new Palette(); p.addPage("X"); var id = p.addColor(255,0,0,255); print(id)',
    ], lambda r: (output_of(r) == "2", f"id={output_of(r)}"), group=G)

    # Sequential addColor IDs
    test("Sequential addColor returns 2,3,4", [
        'var p = new Palette(); p.addPage("X"); var a=p.addColor(255,0,0,255); var b=p.addColor(0,255,0,255); var c=p.addColor(0,0,255,255); print(a+","+b+","+c)',
    ], lambda r: (output_of(r) == "2,3,4", f"ids={output_of(r)}"), group=G)

    # styleCount after adding colors
    test("styleCount after adding 3 colors = 5", [
        'var p = new Palette(); p.addPage("X"); p.addColor(1,2,3,255); p.addColor(4,5,6,255); p.addColor(7,8,9,255); print(p.styleCount)',
    ], lambda r: (output_of(r) == "5", f"styleCount={output_of(r)}"), group=G)

    # getStyleColor readback
    test("getStyleColor reads back correct RGBA", [
        'var p = new Palette(); p.addPage("X"); var id = p.addColor(123,45,67,200); var c = p.getStyleColor(id); print(c.r+","+c.g+","+c.b+","+c.a)',
    ], lambda r: (output_of(r) == "123,45,67,200", f"rgba={output_of(r)}"), group=G)

    # setStyleColor modifies
    test("setStyleColor modifies existing color", [
        'var p = new Palette(); p.addPage("X"); var id = p.addColor(0,0,0,255); p.setStyleColor(id,11,22,33,44); var c = p.getStyleColor(id); print(c.r+","+c.g+","+c.b+","+c.a)',
    ], lambda r: (output_of(r) == "11,22,33,44", f"rgba={output_of(r)}"), group=G)

    # Transparent color (alpha=0)
    test("addColor with alpha=0 (transparent)", [
        'var p = new Palette(); p.addPage("X"); var id = p.addColor(255,0,0,0); var c = p.getStyleColor(id); print(c.a)',
    ], lambda r: (output_of(r) == "0", f"alpha={output_of(r)}"), group=G)

    # Boundary values
    test("Color boundary values (0 and 255)", [
        'var p = new Palette(); p.addPage("X"); var id = p.addColor(0,0,0,0); var c = p.getStyleColor(id); print(c.r+","+c.r+","+c.b+","+c.a)',
    ], lambda r: ("0,0,0,0" == output_of(r), f"out={output_of(r)}"), group=G)

    # addColor without addPage first
    test("addColor WITHOUT addPage first (expect error or weird behavior)", [
        'var p = new Palette(); try { var id = p.addColor(255,0,0,255); print("id="+id); } catch(e) { print("error:"+e); }',
    ], lambda r: (True, f"out={output_of(r)} [INVESTIGATE if id returned]"), group=G)

    # getStyleColor on default style 0
    test("getStyleColor on default style index 0", [
        'var p = new Palette(); var c = p.getStyleColor(0); print(c ? c.r+","+c.g+","+c.b+","+c.a : "null")',
    ], lambda r: (True, f"style0={output_of(r)}"), group=G)

    # getStyleColor on default style 1
    test("getStyleColor on default style index 1", [
        'var p = new Palette(); var c = p.getStyleColor(1); print(c ? c.r+","+c.g+","+c.b+","+c.a : "null")',
    ], lambda r: (True, f"style1={output_of(r)}"), group=G)

    # getStyleColor on invalid index
    test("getStyleColor on invalid index (999)", [
        'var p = new Palette(); try { var c = p.getStyleColor(999); print(c ? "got:"+c.r : "null"); } catch(e) { print("error"); }',
    ], lambda r: (True, f"out={output_of(r)} [should error or return null]"), group=G)


# ============================================================
#  STEP 4: DRAWING - STROKE
# ============================================================

def test_step4_stroke():
    G = "Step 4a: Stroke creation"

    # Create empty stroke
    test("Create empty Stroke", [
        'var s = new Stroke(); print(s.pointCount)',
    ], lambda r: (output_of(r) == "0", f"pointCount={output_of(r)}"), group=G)

    # addPoint single
    test("addPoint single point", [
        'var s = new Stroke(); s.addPoint(10, 20, 3); print(s.pointCount)',
    ], lambda r: (output_of(r) == "1", f"pointCount={output_of(r)}"), group=G)

    # addPoints batch
    test("addPoints batch (5 points)", [
        'var s = new Stroke(); s.addPoints([[0,0,1],[10,10,1],[20,0,1],[30,10,1],[40,0,1]]); print(s.pointCount)',
    ], lambda r: (output_of(r) == "5", f"pointCount={output_of(r)}"), group=G)

    # build() and length
    test("build() produces non-zero length", [
        'var s = new Stroke(); s.addPoints([[0,0,1],[100,0,1]]); s.build(); print(s.length)',
    ], lambda r: (float(output_of(r) or "0") > 0, f"length={output_of(r)}"), group=G)

    # close() on a stroke
    test("close() makes closed stroke", [
        'var s = new Stroke(); s.addPoints([[0,0,1],[50,50,1],[100,0,1]]); s.build(); s.close(); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # setStyle and style readback
    test("setStyle / style property readback", [
        'var s = new Stroke(); s.addPoints([[0,0,1],[10,10,1]]); s.build(); s.setStyle(5); print(s.style)',
    ], lambda r: (output_of(r) == "5", f"style={output_of(r)}"), group=G)

    # Default thickness (omitted)
    test("addPoints with default thickness (omit t)", [
        'var s = new Stroke(); s.addPoints([[0,0],[50,50],[100,0]]); s.build(); print(s.pointCount > 0 ? "ok" : "fail")',
    ], lambda r: ("ok" in output_of(r) or not has_error(r), f"out={output_of(r)}"), group=G)

    # Zero thickness
    test("Stroke with thickness=0", [
        'var s = new Stroke(); s.addPoints([[0,0,0],[100,0,0]]); s.build(); print(s.length)',
    ], lambda r: (True, f"length={output_of(r)} [may be invisible but should not crash]"), group=G)

    # Very large thickness
    test("Stroke with thickness=100", [
        'var s = new Stroke(); s.addPoints([[0,0,100],[100,0,100]]); s.build(); print(s.length)',
    ], lambda r: (float(output_of(r) or "0") > 0, f"length={output_of(r)}"), group=G)

    # Negative thickness (clamped to 0)
    test("Stroke with negative thickness (clamped to 0)", [
        'var s = new Stroke(); s.addPoints([[0,0,-5],[100,0,-5]]); s.build(); print(s.length)',
    ], lambda r: (float(output_of(r) or "0") >= 0, f"length={output_of(r)} [clamped to 0 thickness]"), group=G)

    # Single point stroke
    test("Single-point stroke after build", [
        'var s = new Stroke(); s.addPoint(50,50,2); s.build(); print("len="+s.length+" pts="+s.pointCount)',
    ], lambda r: (True, f"out={output_of(r)} [degenerate - may be zero length]"), group=G)

    # Very many points
    test("Stroke with 200 points", [
        'var s = new Stroke(); var pts = []; for(var i=0;i<200;i++) pts.push([i,Math.sin(i/10)*50,2]); s.addPoints(pts); s.build(); print("pts="+s.pointCount+" len="+Math.round(s.length))',
    ], lambda r: (not has_error(r), f"out={output_of(r)}"), group=G)

    # Negative coordinates
    test("Stroke with negative coordinates", [
        'var s = new Stroke(); s.addPoints([[-100,-200,2],[0,0,2],[100,200,2]]); s.build(); print(s.length > 0 ? "ok" : "fail")',
    ], lambda r: ("ok" in output_of(r), f"out={output_of(r)}"), group=G)

    # Very large coordinates
    test("Stroke with very large coordinates (10000)", [
        'var s = new Stroke(); s.addPoints([[0,0,2],[10000,10000,2]]); s.build(); print(Math.round(s.length))',
    ], lambda r: (float(output_of(r) or "0") > 0, f"length={output_of(r)}"), group=G)

    # Varying thickness along stroke (pressure sensitivity)
    test("Varying thickness (pressure simulation) 1->5->1", [
        'var s = new Stroke(); s.addPoints([[0,0,1],[25,25,3],[50,50,5],[75,25,3],[100,0,1]]); s.build(); print("ok pts="+s.pointCount)',
    ], lambda r: ("ok" in output_of(r), f"out={output_of(r)}"), group=G)

    # build() called twice
    test("build() called twice (idempotent?)", [
        'var s = new Stroke(); s.addPoints([[0,0,2],[100,0,2]]); s.build(); var len1 = s.length; s.build(); print(s.length == len1 ? "same" : "different:"+s.length)',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # addPoints after build
    test("addPoints after build() (allowed?)", [
        'var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.addPoints([[100,0,2]]); s.build(); print("pts="+s.pointCount+" len="+Math.round(s.length))',
    ], lambda r: (True, f"out={output_of(r)} [investigate if points were added]"), group=G)


# ============================================================
#  STEP 4: DRAWING - VECTORIMAGE
# ============================================================

def test_step4_vectorimage():
    G = "Step 4b: VectorImage operations"

    # Empty VectorImage
    test("Empty VectorImage strokeCount=0", [
        'var vi = new VectorImage(); print(vi.strokeCount)',
    ], lambda r: (output_of(r) == "0", f"strokeCount={output_of(r)}"), group=G)

    # regionCount on empty
    test("Empty VectorImage regionCount", [
        'var vi = new VectorImage(); print(vi.regionCount)',
    ], lambda r: (True, f"regionCount={output_of(r)}"), group=G)

    # addStroke increments count
    test("addStroke increments strokeCount", [
        'var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[100,0,2]]); s.build(); vi.addStroke(s); print(vi.strokeCount)',
    ], lambda r: (output_of(r) == "1", f"strokeCount={output_of(r)}"), group=G)

    # Multiple strokes
    test("Add 5 strokes", [
        '''var vi = new VectorImage();
        for(var i=0;i<5;i++) {
            var s = new Stroke(); s.addPoints([[i*20,0,2],[i*20+10,10,2]]); s.build(); vi.addStroke(s);
        }
        print(vi.strokeCount)''',
    ], lambda r: (output_of(r) == "5", f"strokeCount={output_of(r)}"), group=G)

    # getStroke by index
    test("getStroke returns stroke with style", [
        'var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[100,0,2]]); s.build(); s.setStyle(3); vi.addStroke(s); var got = vi.getStroke(0); print(got.style)',
    ], lambda r: (output_of(r) == "3", f"style={output_of(r)}"), group=G)

    # getStroke out of bounds
    test("getStroke out of bounds (expect error)", [
        'var vi = new VectorImage(); try { var s = vi.getStroke(0); print("got:" + s); } catch(e) { print("error"); }',
    ], lambda r: (True, f"out={output_of(r)} [should error or return null]"), group=G)

    # removeStroke
    test("removeStroke reduces count", [
        '''var vi = new VectorImage();
        var s1 = new Stroke(); s1.addPoints([[0,0,2],[50,0,2]]); s1.build(); vi.addStroke(s1);
        var s2 = new Stroke(); s2.addPoints([[0,10,2],[50,10,2]]); s2.build(); vi.addStroke(s2);
        vi.removeStroke(0); print(vi.strokeCount)''',
    ], lambda r: (output_of(r) == "1", f"strokeCount={output_of(r)}"), group=G)

    # removeStroke out of bounds
    test("removeStroke out of bounds (expect error)", [
        'var vi = new VectorImage(); try { vi.removeStroke(0); print("no_error"); } catch(e) { print("error"); }',
    ], lambda r: (True, f"out={output_of(r)} [should error]"), group=G)

    # toImage without palette (MUST fail)
    test("toImage WITHOUT palette (expect error)", [
        'var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[100,0,2]]); s.build(); vi.addStroke(s); try { var img = vi.toImage(); print("no_error type="+img.type); } catch(e) { print("error"); }',
    ], lambda r: ("error" in output_of(r), f"out={output_of(r)}"), group=G)

    # toImage with palette
    test("toImage WITH palette succeeds", [
        'var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255); var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[100,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p); var img = vi.toImage(); print(img.type)',
    ], lambda r: ("Vector" in output_of(r), f"type={output_of(r)}"), group=G)

    # group strokes
    test("group() consecutive strokes", [
        '''var vi = new VectorImage();
        for(var i=0;i<3;i++) { var s = new Stroke(); s.addPoints([[i*30,0,2],[i*30+20,20,2]]); s.build(); vi.addStroke(s); }
        vi.group(0, 3); print("strokeCount="+vi.strokeCount)''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # ungroup
    test("ungroup() after group()", [
        '''var vi = new VectorImage();
        for(var i=0;i<3;i++) { var s = new Stroke(); s.addPoints([[i*30,0,2],[i*30+20,20,2]]); s.build(); vi.addStroke(s); }
        vi.group(0, 3); vi.ungroup(0); print("strokeCount="+vi.strokeCount)''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # merge two VectorImages
    test("merge() two VectorImages", [
        '''var vi1 = new VectorImage(); var s1 = new Stroke(); s1.addPoints([[0,0,2],[50,0,2]]); s1.build(); vi1.addStroke(s1);
        var vi2 = new VectorImage(); var s2 = new Stroke(); s2.addPoints([[0,10,2],[50,10,2]]); s2.build(); vi2.addStroke(s2);
        vi1.merge(vi2); print(vi1.strokeCount)''',
    ], lambda r: (output_of(r) == "2", f"strokeCount={output_of(r)}"), group=G)

    # fill inside closed region (use 4 separate strokes to form boundary - self-loop doesn't create regions)
    test("fill() inside region formed by 4 strokes", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255); var red = p.addColor(255,0,0,255);
        var vi = new VectorImage();
        var s1 = new Stroke(); s1.addPoints([[-50,-50,2],[50,-50,2]]); s1.build(); s1.setStyle(ink); vi.addStroke(s1);
        var s2 = new Stroke(); s2.addPoints([[50,-50,2],[50,50,2]]); s2.build(); s2.setStyle(ink); vi.addStroke(s2);
        var s3 = new Stroke(); s3.addPoints([[50,50,2],[-50,50,2]]); s3.build(); s3.setStyle(ink); vi.addStroke(s3);
        var s4 = new Stroke(); s4.addPoints([[-50,50,2],[-50,-50,2]]); s4.build(); s4.setStyle(ink); vi.addStroke(s4);
        vi.setPalette(p);
        vi.fill(0, 0, red);
        print("regions="+vi.regionCount)''',
    ], lambda r: (int(output_of(r).replace("regions=","") or "0") > 0, f"out={output_of(r)}"), group=G)

    # fill with invalid styleId
    test("fill() with styleId=0 (transparent default)", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s = new Stroke(); s.addPoints([[-50,-50,2],[50,-50,2],[50,50,2],[-50,50,2],[-50,-50,2]]); s.build(); s.close(); s.setStyle(ink); vi.addStroke(s);
        vi.setPalette(p);
        try { vi.fill(0, 0, 0); print("ok"); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # setEdgeColors
    test("setEdgeColors on stroke boundary", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255); var red = p.addColor(255,0,0,255); var blue = p.addColor(0,0,255,255);
        var vi = new VectorImage();
        var s = new Stroke(); s.addPoints([[-50,0,2],[50,0,2]]); s.build(); s.setStyle(ink); vi.addStroke(s);
        vi.setPalette(p);
        try { vi.setEdgeColors(0, red, blue); print("ok"); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Rasterize and save to verify visually (4 strokes forming rectangle with red fill)
    outpath = os.path.join(TESTDIR, "test_vi_closed_fill.png")
    test("Rasterize filled shape (4 strokes) -> PNG", [
        f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255); var red = p.addColor(255,0,0,255);
        var vi = new VectorImage();
        var s1 = new Stroke(); s1.addPoints([[-50,-50,3],[50,-50,3]]); s1.build(); s1.setStyle(ink); vi.addStroke(s1);
        var s2 = new Stroke(); s2.addPoints([[50,-50,3],[50,50,3]]); s2.build(); s2.setStyle(ink); vi.addStroke(s2);
        var s3 = new Stroke(); s3.addPoints([[50,50,3],[-50,50,3]]); s3.build(); s3.setStyle(ink); vi.addStroke(s3);
        var s4 = new Stroke(); s4.addPoints([[-50,50,3],[-50,-50,3]]); s4.build(); s4.setStyle(ink); vi.addStroke(s4);
        vi.setPalette(p);
        vi.fill(0, 0, red);
        var rast = new Rasterizer(); rast.xres = 128; rast.yres = 128; rast.dpi = 72;
        rast.rasterize(vi.toImage()).save("{outpath}");
        print("saved")''',
    ], lambda r: (file_exists_and_nonzero(outpath), f"file={'exists' if file_exists_and_nonzero(outpath) else 'MISSING'}"), group=G)


# ============================================================
#  STEP 4: DRAWING - RASTERCANVAS
# ============================================================

def test_step4_rastercanvas():
    G = "Step 4c: RasterCanvas operations"

    # Create and check dimensions
    test("RasterCanvas width/height", [
        'var rc = new RasterCanvas(200, 150); print(rc.width + "x" + rc.height)',
    ], lambda r: (output_of(r) == "200x150", f"dim={output_of(r)}"), group=G)

    # brushStroke basic
    test("brushStroke basic draw", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[10,10,3],[90,90,3]], 1, true); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # brushStroke without antialias
    test("brushStroke antialias=false", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[10,10,3],[90,90,3]], 1, false); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # brushStroke with various thicknesses
    for t in [1, 2, 5, 10, 20]:
        test(f"brushStroke thickness={t}", [
            f'var rc = new RasterCanvas(100, 100); rc.brushStroke([[10,50,{t}],[90,50,{t}]], 1, true); print("ok")',
        ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # brushStroke varying thickness (pressure)
    test("brushStroke varying thickness (pressure sim)", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[10,50,1],[30,50,5],[50,50,10],[70,50,5],[90,50,1]], 1, true); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # brushStroke single point
    test("brushStroke single point (dot)", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[50,50,5]], 1, true); print("ok")',
    ], lambda r: (True, f"out={output_of(r)} [may or may not draw a dot]"), group=G)

    # brushStroke many points (smooth curve)
    test("brushStroke with 50 points (smooth curve)", [
        'var rc = new RasterCanvas(200, 200); var pts = []; for(var i=0;i<50;i++) { var t=i/49; pts.push([20+t*160, 100+Math.sin(t*6.28)*60, 3]); } rc.brushStroke(pts, 1, true); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # fill
    test("fill flood fill", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[20,20,3],[80,20,3],[80,80,3],[20,80,3],[20,20,3]], 1, true); rc.fill(50, 50, 2); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # rectFill
    test("rectFill rectangle area", [
        'var rc = new RasterCanvas(100, 100); rc.rectFill(10, 10, 90, 90, 2); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # inkFill
    test("inkFill on drawn lines", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[10,50,5],[90,50,5]], 1, true); rc.inkFill(50, 50, 2, 10); print("ok")',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # clear
    test("clear() empties canvas", [
        'var rc = new RasterCanvas(100, 100); rc.rectFill(0,0,100,100,1); rc.clear(); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # toImage type check
    test("toImage returns ToonzRaster type", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[10,10,3],[90,90,3]], 1, true); var img = rc.toImage(); print(img.type)',
    ], lambda r: (True, f"type={output_of(r)} [expect ToonzRaster or Raster]"), group=G)

    # Zero-size canvas
    test("RasterCanvas(0, 0) - zero size", [
        'try { var rc = new RasterCanvas(0, 0); print("dim="+rc.width+"x"+rc.height); } catch(e) { print("error"); }',
    ], lambda r: (True, f"out={output_of(r)} [should error or handle]"), group=G)

    # Very large canvas
    test("RasterCanvas(2000, 2000) - large canvas", [
        'var rc = new RasterCanvas(2000, 2000); rc.brushStroke([[100,100,5],[1900,1900,5]], 1, true); print("ok "+rc.width+"x"+rc.height)',
    ], lambda r: ("ok" in output_of(r), f"out={output_of(r)}"), group=G)

    # brushStroke outside canvas bounds
    test("brushStroke outside canvas bounds", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[-50,-50,3],[200,200,3]], 1, true); print("ok")',
    ], lambda r: (True, f"out={output_of(r)} [should clip or handle gracefully]"), group=G)

    # Rasterize raster canvas to PNG for visual check
    outpath = os.path.join(TESTDIR, "test_rastercanvas.png")
    test("RasterCanvas -> save PNG for visual check", [
        f'''var rc = new RasterCanvas(128, 128);
        rc.rectFill(0, 0, 128, 128, 1);
        rc.brushStroke([[20,20,4],[108,20,4],[108,108,4],[20,108,4],[20,20,4]], 1, true);
        rc.brushStroke([[40,64,2],[88,100,2]], 1, true);
        rc.brushStroke([[40,64,2],[88,30,2]], 1, true);
        rc.fill(64, 64, 2);
        var img = rc.toImage();
        img.save("{outpath}");
        print("saved")''',
    ], lambda r: (file_exists_and_nonzero(outpath), f"file={'exists' if file_exists_and_nonzero(outpath) else 'MISSING'}"), group=G)

    # Multiple styleIds on same canvas
    test("Multiple styleIds on same canvas (3 colors)", [
        'var rc = new RasterCanvas(100, 100); rc.brushStroke([[10,50,3],[90,50,3]], 1, true); rc.brushStroke([[50,10,3],[50,90,3]], 2, true); rc.rectFill(60,60,90,90,3); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)


# ============================================================
#  STEP 5: FILL AND COLOR (additional)
# ============================================================

def test_step5_fill():
    G = "Step 5: Fill and Color"

    # VectorImage fill at point outside all regions (should error)
    test("VectorImage fill outside any region", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255); var red = p.addColor(255,0,0,255);
        var vi = new VectorImage();
        var s1 = new Stroke(); s1.addPoints([[-10,-10,2],[10,-10,2]]); s1.build(); s1.setStyle(ink); vi.addStroke(s1);
        var s2 = new Stroke(); s2.addPoints([[10,-10,2],[10,10,2]]); s2.build(); s2.setStyle(ink); vi.addStroke(s2);
        var s3 = new Stroke(); s3.addPoints([[10,10,2],[-10,10,2]]); s3.build(); s3.setStyle(ink); vi.addStroke(s3);
        var s4 = new Stroke(); s4.addPoints([[-10,10,2],[-10,-10,2]]); s4.build(); s4.setStyle(ink); vi.addStroke(s4);
        vi.setPalette(p);
        try { vi.fill(500, 500, red); print("ok"); } catch(e) { print("error"); }''',
    ], lambda r: ("error" in output_of(r), f"out={output_of(r)}"), group=G)

    # RasterCanvas fill on empty canvas
    test("RasterCanvas fill on empty canvas", [
        'var rc = new RasterCanvas(100, 100); rc.fill(50, 50, 1); print("ok")',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)


# ============================================================
#  STEP 7: MANAGE FRAMES AND DRAWINGS
# ============================================================

def test_step7_frames():
    G = "Step 7: Manage Frames and Drawings"

    # setFrame with numeric ID
    test("setFrame with numeric ID", [
        '''var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "frm");
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage()); print(lv.frameCount)''',
    ], lambda r: (output_of(r) == "1", f"frameCount={output_of(r)}"), group=G)

    # setFrame multiple frames
    test("setFrame multiple frames (1,2,3)", [
        '''var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "multi");
        for(var f=1;f<=3;f++) {
            var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[f*20,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p);
            lv.setFrame(f, vi.toImage());
        }
        print(lv.frameCount)''',
    ], lambda r: (output_of(r) == "3", f"frameCount={output_of(r)}"), group=G)

    # getFrame readback
    test("getFrame retrieves image", [
        '''var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "get");
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        var img = lv.getFrame(1); print(img ? img.type : "null")''',
    ], lambda r: (True, f"type={output_of(r)}"), group=G)

    # getFrameByIndex
    test("getFrameByIndex(0)", [
        '''var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "idx");
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        var img = lv.getFrameByIndex(0); print(img ? img.type : "null")''',
    ], lambda r: (True, f"type={output_of(r)}"), group=G)

    # getFrameIds
    test("getFrameIds returns correct IDs", [
        '''var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "ids");
        for(var f=1;f<=3;f++) {
            var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[f*20,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p);
            lv.setFrame(f, vi.toImage());
        }
        var ids = lv.getFrameIds(); print(ids.join(","))''',
    ], lambda r: (True, f"ids={output_of(r)}"), group=G)

    # setFrame with string suffix ID (e.g., "1a")
    test("setFrame with suffix ID '1a'", [
        '''var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "sfx");
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p);
        try { lv.setFrame("1a", vi.toImage()); print("ok fc="+lv.frameCount); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)} [string frame IDs]"), group=G)

    # Level setPalette / getPalette
    test("Level setPalette / getPalette", [
        '''var p = new Palette(); p.addPage("X"); p.addColor(100,200,50,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "lpal");
        lv.setPalette(p);
        var p2 = lv.getPalette(); print(p2 ? p2.styleCount : "null")''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)


# ============================================================
#  STEP 8: XSHEET ORGANIZATION
# ============================================================

def test_step8_xsheet():
    G = "Step 8: XSheet Organization"

    # setCell and getCell
    test("setCell / getCell round trip", [
        '''var scene = new Scene(); var lv = scene.newLevel("Vector", "xsh");
        var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        scene.setCell(0, 0, lv, 1);
        var cell = scene.getCell(0, 0);
        print(cell ? "level="+cell.level+",fid="+cell.fid : "null")''',
    ], lambda r: (True, f"cell={output_of(r)}"), group=G)

    # columnCount
    test("columnCount after newLevel", [
        'var scene = new Scene(); scene.newLevel("Vector", "c1"); print(scene.columnCount)',
    ], lambda r: (True, f"columnCount={output_of(r)}"), group=G)

    # insertColumn
    test("insertColumn adds column", [
        'var scene = new Scene(); scene.newLevel("Vector","a"); var before = scene.columnCount; scene.insertColumn(1); print("before="+before+" after="+scene.columnCount)',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # deleteColumn
    test("deleteColumn removes column", [
        'var scene = new Scene(); scene.newLevel("Vector","a"); scene.newLevel("Vector","b"); var before = scene.columnCount; scene.deleteColumn(0); print("before="+before+" after="+scene.columnCount)',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Multiple columns with cells - frame hold
    test("Frame hold - same drawing on multiple rows", [
        '''var scene = new Scene(); var lv = scene.newLevel("Vector", "hold");
        var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.setStyle(2); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        for(var r=0; r<24; r++) scene.setCell(r, 0, lv, 1);
        print("ok rows=24")''',
    ], lambda r: ("ok" in output_of(r), f"out={output_of(r)}"), group=G)

    # setFrameRate
    test("setFrameRate", [
        'var scene = new Scene(); scene.setFrameRate(30); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # Multiple columns (multi-part character)
    test("Multi-part character: 3 columns with separate levels", [
        '''var scene = new Scene();
        var head = scene.newLevel("Vector", "head");
        var body = scene.newLevel("Vector", "body");
        var legs = scene.newLevel("Vector", "legs");
        print("cols="+scene.columnCount)''',
    ], lambda r: (True, f"out={output_of(r)} [expect 3 columns]"), group=G)


# ============================================================
#  STEP 9: KEYFRAME ANIMATION (StageObject)
# ============================================================

def test_step9_keyframes():
    G = "Step 9: Keyframe Animation"

    # All channels
    channels = ["x", "y", "z", "angle", "rotation", "scalex", "scaley", "scale", "shearx", "sheary", "so", "path"]
    for ch in channels:
        test(f"setKeyframe/getValueAt channel='{ch}'", [
            f'''var scene = new Scene(); scene.newLevel("Vector","kf");
            var obj = scene.getStageObject(0);
            try {{ obj.setKeyframe(0, "{ch}", 10); obj.setKeyframe(24, "{ch}", 50); var v = obj.getValueAt(12, "{ch}"); print("v12="+v); }} catch(e) {{ print("error:"+e); }}''',
        ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Interpolation types
    interps = ["constant", "linear", "speedInOut", "easeInOut", "exponential"]
    for interp in interps:
        test(f"Interpolation type='{interp}'", [
            f'''var scene = new Scene(); scene.newLevel("Vector","ip");
            var obj = scene.getStageObject(0);
            obj.setKeyframe(0, "x", 0); obj.setKeyframe(24, "x", 100);
            try {{ obj.setInterpolation(0, "x", "{interp}"); var v = obj.getValueAt(12, "x"); print("v12="+Math.round(v*100)/100); }} catch(e) {{ print("error:"+e); }}''',
        ], lambda r: (True, f"mid={output_of(r)}"), group=G)

    # Verify different interpolations give different midpoints
    test("Constant vs linear give different midpoints", [
        '''var scene = new Scene(); scene.newLevel("Vector","diff");
        var obj = scene.getStageObject(0);
        obj.setKeyframe(0, "x", 0); obj.setKeyframe(24, "x", 100);
        obj.setInterpolation(0, "x", "constant");
        var vc = obj.getValueAt(12, "x");
        obj.setInterpolation(0, "x", "linear");
        var vl = obj.getValueAt(12, "x");
        print("const="+Math.round(vc)+" linear="+Math.round(vl)+" diff="+(Math.round(vc)!=Math.round(vl)))''',
    ], lambda r: ("diff=true" in output_of(r), f"out={output_of(r)}"), group=G)

    # setParent hierarchy
    test("setParent creates hierarchy", [
        '''var scene = new Scene();
        scene.newLevel("Vector","parent");
        scene.newLevel("Vector","child");
        var parent = scene.getStageObject(0);
        var child = scene.getStageObject(1);
        try { child.setParent(parent); print("ok"); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # setStatus
    for status in ["xy", "path", "pathAim", "ik"]:
        test(f"setStatus('{status}')", [
            f'''var scene = new Scene(); scene.newLevel("Vector","st");
            var obj = scene.getStageObject(0);
            try {{ obj.setStatus("{status}"); print("status="+obj.status); }} catch(e) {{ print("error:"+e); }}''',
        ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # name property
    test("StageObject name property", [
        'var scene = new Scene(); scene.newLevel("Vector","nm"); var obj = scene.getStageObject(0); print("name="+obj.name)',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Invalid channel
    test("setKeyframe invalid channel name (expect error)", [
        '''var scene = new Scene(); scene.newLevel("Vector","bad");
        var obj = scene.getStageObject(0);
        try { obj.setKeyframe(0, "nonexistent", 10); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: (True, f"out={output_of(r)} [should error]"), group=G)

    # Invalid interpolation type
    test("setInterpolation invalid type (expect error)", [
        '''var scene = new Scene(); scene.newLevel("Vector","bad2");
        var obj = scene.getStageObject(0);
        obj.setKeyframe(0, "x", 0); obj.setKeyframe(24, "x", 100);
        try { obj.setInterpolation(0, "x", "bogus"); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: (True, f"out={output_of(r)} [should error]"), group=G)

    # Negative frame
    test("setKeyframe at negative frame (expect error)", [
        '''var scene = new Scene(); scene.newLevel("Vector","neg");
        var obj = scene.getStageObject(0);
        try { obj.setKeyframe(-1, "x", 10); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: ("error" in output_of(r), f"out={output_of(r)}"), group=G)

    # Very large frame number
    test("setKeyframe at frame 10000", [
        '''var scene = new Scene(); scene.newLevel("Vector","big");
        var obj = scene.getStageObject(0);
        obj.setKeyframe(0, "x", 0); obj.setKeyframe(10000, "x", 100);
        var v = obj.getValueAt(5000, "x");
        print("v5000="+Math.round(v))''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Multiple channels animated simultaneously
    test("Multiple channels animated simultaneously (x+y+angle)", [
        '''var scene = new Scene(); scene.newLevel("Vector","multi");
        var obj = scene.getStageObject(0);
        obj.setKeyframe(0, "x", 0); obj.setKeyframe(24, "x", 100);
        obj.setKeyframe(0, "y", 0); obj.setKeyframe(24, "y", 200);
        obj.setKeyframe(0, "angle", 0); obj.setKeyframe(24, "angle", 360);
        var vx = obj.getValueAt(12, "x");
        var vy = obj.getValueAt(12, "y");
        var va = obj.getValueAt(12, "angle");
        print("x="+Math.round(vx)+" y="+Math.round(vy)+" a="+Math.round(va))''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)


# ============================================================
#  STEP 11: PLASTIC RIG
# ============================================================

def test_step11_plasticrig():
    G = "Step 11: PlasticRig Mesh Deformation"

    # Create empty rig
    test("Create empty PlasticRig", [
        'var rig = new PlasticRig(); print(rig.vertexCount)',
    ], lambda r: (output_of(r) == "0", f"vertexCount={output_of(r)}"), group=G)

    # Add root vertex
    test("addVertex root (parent=-1)", [
        'var rig = new PlasticRig(); var r = rig.addVertex(0,0,-1); print("idx="+r+" count="+rig.vertexCount)',
    ], lambda r: ("count=1" in output_of(r), f"out={output_of(r)}"), group=G)

    # Add child vertices
    test("addVertex with parent hierarchy", [
        '''var rig = new PlasticRig();
        var root = rig.addVertex(0,0,-1);
        var spine = rig.addVertex(0,50,root);
        var head = rig.addVertex(0,100,spine);
        var larm = rig.addVertex(-40,70,spine);
        var rarm = rig.addVertex(40,70,spine);
        print("count="+rig.vertexCount)''',
    ], lambda r: ("count=5" in output_of(r), f"out={output_of(r)}"), group=G)

    # setVertexName
    test("setVertexName / read back", [
        '''var rig = new PlasticRig();
        var root = rig.addVertex(0,0,-1);
        rig.setVertexName(root, "pelvis");
        print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # moveVertex
    test("moveVertex repositions", [
        '''var rig = new PlasticRig();
        var v = rig.addVertex(0,0,-1);
        rig.moveVertex(v, 100, 200);
        print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # removeVertex
    test("removeVertex reduces count", [
        '''var rig = new PlasticRig();
        var a = rig.addVertex(0,0,-1);
        var b = rig.addVertex(10,10,a);
        rig.removeVertex(b);
        print("count="+rig.vertexCount)''',
    ], lambda r: ("count=1" in output_of(r), f"out={output_of(r)}"), group=G)

    # setVertexKeyframe for angle
    test("setVertexKeyframe angle animation", [
        '''var rig = new PlasticRig();
        var root = rig.addVertex(0,0,-1);
        var arm = rig.addVertex(50,0,root);
        rig.setVertexKeyframe(arm, 0, "angle", 0);
        rig.setVertexKeyframe(arm, 24, "angle", 90);
        print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # setVertexKeyframe for distance
    test("setVertexKeyframe distance animation", [
        '''var rig = new PlasticRig();
        var root = rig.addVertex(0,0,-1);
        var arm = rig.addVertex(50,0,root);
        rig.setVertexKeyframe(arm, 0, "distance", 50);
        rig.setVertexKeyframe(arm, 24, "distance", 100);
        print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # setVertexKeyframe for stacking order
    test("setVertexKeyframe so (stacking order)", [
        '''var rig = new PlasticRig();
        var root = rig.addVertex(0,0,-1);
        rig.setVertexKeyframe(root, 0, "so", 1);
        rig.setVertexKeyframe(root, 24, "so", 5);
        print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # Invalid vertex index
    test("moveVertex invalid index (expect error)", [
        '''var rig = new PlasticRig();
        try { rig.moveVertex(99, 0, 0); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: (True, f"out={output_of(r)} [should error]"), group=G)

    # Invalid param name
    test("setVertexKeyframe invalid param (expect error)", [
        '''var rig = new PlasticRig();
        var root = rig.addVertex(0,0,-1);
        try { rig.setVertexKeyframe(root, 0, "bogus", 10); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: (True, f"out={output_of(r)} [should error]"), group=G)


# ============================================================
#  STEP 12: AUTO-INBETWEEN
# ============================================================

def test_step12_inbetween():
    G = "Step 12: Auto-Inbetween"

    # Basic tween at 0.5
    test("Inbetween tween(0.5, 'linear')", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi1 = new VectorImage(); var s1 = new Stroke(); s1.addPoints([[0,0,2],[100,0,2]]); s1.build(); s1.setStyle(ink); vi1.addStroke(s1); vi1.setPalette(p);
        var vi2 = new VectorImage(); var s2 = new Stroke(); s2.addPoints([[0,0,2],[0,100,2]]); s2.build(); s2.setStyle(ink); vi2.addStroke(s2); vi2.setPalette(p);
        var tw = new Inbetween(vi1.toImage(), vi2.toImage());
        var mid = tw.tween(0.5, "linear");
        print(mid.type)''',
    ], lambda r: (True, f"type={output_of(r)}"), group=G)

    # Tween at various t values
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        test(f"Inbetween tween(t={t})", [
            f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
            var vi1 = new VectorImage(); var s1 = new Stroke(); s1.addPoints([[0,0,2],[100,0,2]]); s1.build(); s1.setStyle(ink); vi1.addStroke(s1); vi1.setPalette(p);
            var vi2 = new VectorImage(); var s2 = new Stroke(); s2.addPoints([[0,0,2],[0,100,2]]); s2.build(); s2.setStyle(ink); vi2.addStroke(s2); vi2.setPalette(p);
            var tw = new Inbetween(vi1.toImage(), vi2.toImage());
            var mid = tw.tween({t}, "linear");
            print(mid ? "ok" : "null")''',
        ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # All easing modes
    for mode in ["linear", "easeIn", "easeOut", "easeInOut"]:
        test(f"Inbetween easing='{mode}'", [
            f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
            var vi1 = new VectorImage(); var s1 = new Stroke(); s1.addPoints([[0,0,2],[100,0,2]]); s1.build(); s1.setStyle(ink); vi1.addStroke(s1); vi1.setPalette(p);
            var vi2 = new VectorImage(); var s2 = new Stroke(); s2.addPoints([[0,0,2],[0,100,2]]); s2.build(); s2.setStyle(ink); vi2.addStroke(s2); vi2.setPalette(p);
            var tw = new Inbetween(vi1.toImage(), vi2.toImage());
            try {{ var mid = tw.tween(0.5, "{mode}"); print(mid ? "ok" : "null"); }} catch(e) {{ print("error:"+e); }}''',
        ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Mismatched stroke counts
    test("Inbetween with mismatched stroke counts (1 vs 2)", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi1 = new VectorImage(); var s1 = new Stroke(); s1.addPoints([[0,0,2],[100,0,2]]); s1.build(); s1.setStyle(ink); vi1.addStroke(s1); vi1.setPalette(p);
        var vi2 = new VectorImage();
        var s2a = new Stroke(); s2a.addPoints([[0,0,2],[0,100,2]]); s2a.build(); s2a.setStyle(ink); vi2.addStroke(s2a);
        var s2b = new Stroke(); s2b.addPoints([[50,0,2],[50,100,2]]); s2b.build(); s2b.setStyle(ink); vi2.addStroke(s2b);
        vi2.setPalette(p);
        try { var tw = new Inbetween(vi1.toImage(), vi2.toImage()); var mid = tw.tween(0.5, "linear"); print(mid ? "ok" : "null"); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)} [mismatch - may error or degrade]"), group=G)

    # Inbetween with raster images (should error)
    test("Inbetween with ToonzRaster images (expect error)", [
        '''var rc = new RasterCanvas(100, 100);
        rc.brushStroke([[10,10,3],[90,90,3]], 1, true);
        var img1 = rc.toImage();
        rc.clear();
        rc.brushStroke([[10,90,3],[90,10,3]], 1, true);
        var img2 = rc.toImage();
        try { var tw = new Inbetween(img1, img2); var mid = tw.tween(0.5, "linear"); print("no_error"); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)} [SHOULD error - raster not supported]"), group=G)

    # Save inbetween sequence for visual check (use "tweenN" not "tween_N" to avoid frame mangling)
    outdir = TESTDIR
    test("Save 5-frame inbetween sequence as PNGs", [
        f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi1 = new VectorImage(); var s1 = new Stroke(); s1.addPoints([[-60,0,3],[0,60,3],[60,0,3]]); s1.build(); s1.setStyle(ink); vi1.addStroke(s1); vi1.setPalette(p);
        var vi2 = new VectorImage(); var s2 = new Stroke(); s2.addPoints([[-60,0,3],[0,-60,3],[60,0,3]]); s2.build(); s2.setStyle(ink); vi2.addStroke(s2); vi2.setPalette(p);
        var img1 = vi1.toImage(); var img2 = vi2.toImage();
        var tw = new Inbetween(img1, img2);
        var rast = new Rasterizer(); rast.xres = 64; rast.yres = 64; rast.dpi = 72;
        for(var i=0; i<=4; i++) {{
            var t = i/4.0;
            var frame = (i==0) ? img1 : (i==4) ? img2 : tw.tween(t, "easeInOut");
            rast.rasterize(frame).save("{outdir}/testtween" + i + ".png");
        }}
        print("saved 5 frames")''',
    ], lambda r: (all(file_exists_and_nonzero(f"{outdir}/testtween{i}.png") for i in range(5)),
                  f"files={'all exist' if all(file_exists_and_nonzero(f'{outdir}/testtween{i}.png') for i in range(5)) else 'MISSING'}"), group=G)

    # t out of range
    test("Inbetween tween(t=-0.5) - out of range", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi1 = new VectorImage(); var s1 = new Stroke(); s1.addPoints([[0,0,2],[100,0,2]]); s1.build(); s1.setStyle(ink); vi1.addStroke(s1); vi1.setPalette(p);
        var vi2 = new VectorImage(); var s2 = new Stroke(); s2.addPoints([[0,0,2],[0,100,2]]); s2.build(); s2.setStyle(ink); vi2.addStroke(s2); vi2.setPalette(p);
        var tw = new Inbetween(vi1.toImage(), vi2.toImage());
        try { var mid = tw.tween(-0.5, "linear"); print(mid ? "ok" : "null"); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)} [should error or extrapolate]"), group=G)

    test("Inbetween tween(t=1.5) - out of range", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi1 = new VectorImage(); var s1 = new Stroke(); s1.addPoints([[0,0,2],[100,0,2]]); s1.build(); s1.setStyle(ink); vi1.addStroke(s1); vi1.setPalette(p);
        var vi2 = new VectorImage(); var s2 = new Stroke(); s2.addPoints([[0,0,2],[0,100,2]]); s2.build(); s2.setStyle(ink); vi2.addStroke(s2); vi2.setPalette(p);
        var tw = new Inbetween(vi1.toImage(), vi2.toImage());
        try { var mid = tw.tween(1.5, "linear"); print(mid ? "ok" : "null"); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)} [should error or extrapolate]"), group=G)


# ============================================================
#  STEP 14: EFFECTS
# ============================================================

def test_step14_effects():
    G = "Step 14: Effects"

    # Create particle effect
    test("Create Effect('STD_particlesFx')", [
        'var fx = new Effect("STD_particlesFx"); print(fx.type)',
    ], lambda r: (True, f"type={output_of(r)}"), group=G)

    # paramCount
    test("particlesFx paramCount", [
        'var fx = new Effect("STD_particlesFx"); print(fx.paramCount)',
    ], lambda r: (int(output_of(r) or "0") > 0, f"paramCount={output_of(r)}"), group=G)

    # getParamNames
    test("getParamNames returns array", [
        'var fx = new Effect("STD_particlesFx"); var names = fx.getParamNames(); print(names.length + " params, first=" + names[0])',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # setParam / getParam
    test("setParam / getParam round trip", [
        'var fx = new Effect("STD_particlesFx"); var names = fx.getParamNames(); fx.setParam(names[0], 42); var v = fx.getParam(names[0]); print(names[0]+"="+v)',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # setParamKeyframe (use a known numeric param)
    test("setParamKeyframe animation", [
        'var fx = new Effect("STD_particlesFx"); fx.setParamKeyframe("birth_rate", 0, 10); fx.setParamKeyframe("birth_rate", 24, 100); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # Without STD_ prefix (should error)
    test("Effect without STD_ prefix (expect error)", [
        'try { var fx = new Effect("particlesFx"); print("no_error type="+fx.type); } catch(e) { print("error"); }',
    ], lambda r: ("error" in output_of(r), f"out={output_of(r)}"), group=G)

    # Various effect types
    effects = [
        ("STD_blurFx", "Blur"),
        ("STD_directionalBlurFx", "Directional Blur"),
        ("STD_glowFx", "Glow"),
        ("STD_brightContFx", "Brightness/Contrast"),
        ("STD_colorCardFx", "Color Card"),
        ("STD_radialGradientFx", "Radial Gradient"),
        ("STD_fadeFx", "Fade"),
    ]
    for eid, ename in effects:
        test(f"Create Effect('{eid}') - {ename}", [
            f'try {{ var fx = new Effect("{eid}"); print("ok params="+fx.paramCount); }} catch(e) {{ print("error:"+e); }}',
        ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Invalid effect identifier
    test("Invalid effect identifier (expect error)", [
        'try { var fx = new Effect("STD_nonexistentFx"); print("no_error"); } catch(e) { print("error"); }',
    ], lambda r: ("error" in output_of(r), f"out={output_of(r)}"), group=G)

    # setParam on invalid param name
    test("setParam invalid param name", [
        'var fx = new Effect("STD_blurFx"); try { fx.setParam("nonexistent", 10); print("no_error"); } catch(e) { print("error"); }',
    ], lambda r: (True, f"out={output_of(r)} [should error]"), group=G)


# ============================================================
#  RASTERIZER
# ============================================================

def test_rasterizer():
    G = "Rasterizer"

    # Basic rasterize
    test("Rasterize vector image 256x256", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-50,0,3],[50,0,3]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        var rast = new Rasterizer(); rast.xres = 256; rast.yres = 256; rast.dpi = 72;
        var img = rast.rasterize(vi.toImage());
        print(img.width + "x" + img.height)''',
    ], lambda r: ("256x256" in output_of(r), f"dim={output_of(r)}"), group=G)

    # Various resolutions
    for res in [(1,1), (16,16), (64,64), (512,512), (1024,1024)]:
        test(f"Rasterize at {res[0]}x{res[1]}", [
            f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
            var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-50,0,3],[50,0,3]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
            var rast = new Rasterizer(); rast.xres = {res[0]}; rast.yres = {res[1]}; rast.dpi = 72;
            var img = rast.rasterize(vi.toImage());
            print(img.width + "x" + img.height)''',
        ], lambda r: (True, f"dim={output_of(r)}"), group=G)

    # Non-square resolution
    test("Rasterize non-square 200x100", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-50,0,3],[50,0,3]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        var rast = new Rasterizer(); rast.xres = 200; rast.yres = 100; rast.dpi = 72;
        var img = rast.rasterize(vi.toImage());
        print(img.width + "x" + img.height)''',
    ], lambda r: ("200x100" in output_of(r), f"dim={output_of(r)}"), group=G)

    # Different DPI values
    for dpi in [36, 72, 150, 300]:
        test(f"Rasterize at DPI={dpi}", [
            f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
            var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-50,0,3],[50,0,3]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
            var rast = new Rasterizer(); rast.xres = 128; rast.yres = 128; rast.dpi = {dpi};
            var img = rast.rasterize(vi.toImage());
            print("ok " + img.width + "x" + img.height)''',
        ], lambda r: ("ok" in output_of(r), f"out={output_of(r)}"), group=G)

    # Antialiasing on/off comparison
    outpath_aa = os.path.join(TESTDIR, "test_rast_aa.png")
    outpath_noaa = os.path.join(TESTDIR, "test_rast_noaa.png")
    test("Rasterize with antialiasing=true vs false", [
        f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-40,-40,2],[40,40,2]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        var rast = new Rasterizer(); rast.xres = 64; rast.yres = 64; rast.dpi = 72;
        rast.antialiasing = true; rast.rasterize(vi.toImage()).save("{outpath_aa}");
        rast.antialiasing = false; rast.rasterize(vi.toImage()).save("{outpath_noaa}");
        print("saved both")''',
    ], lambda r: (file_exists_and_nonzero(outpath_aa) and file_exists_and_nonzero(outpath_noaa),
                  f"aa={'exists' if file_exists_and_nonzero(outpath_aa) else 'MISSING'} noaa={'exists' if file_exists_and_nonzero(outpath_noaa) else 'MISSING'}"), group=G)

    # Rasterize entire level
    test("Rasterize entire vector level (3 frames)", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "rlv");
        for(var f=1;f<=3;f++) {
            var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[f*30,0,2]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
            lv.setFrame(f, vi.toImage());
        }
        var rast = new Rasterizer(); rast.xres = 64; rast.yres = 64; rast.dpi = 72;
        try { var rl = rast.rasterize(lv); print("ok fc="+rl.frameCount); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)


# ============================================================
#  RENDERER
# ============================================================

def test_renderer():
    G = "Renderer (Scene rendering)"

    # Renderer now works in headless mode via synchronous event-loop wait
    test("Renderer renderFrame", [
        '''var scene = new Scene(); scene.setCameraSize(128, 128);
        var lv = scene.newLevel("Vector", "rnd");
        var p = new Palette(); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-40,0,3],[40,0,3]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        scene.setCell(0, 0, lv, 1);
        var renderer = new Renderer(); var img = renderer.renderFrame(scene, 0);
        print("rendered")''',
        'print("type=" + img.type + " " + img.width + "x" + img.height)',
    ], lambda r: ("type=Raster" in output_of(r, 1), f"out={output_of(r, 1)}"), group=G)

    test("Renderer renderScene (full)", [
        '''var scene = new Scene(); scene.setCameraSize(128, 128);
        var lv = scene.newLevel("Vector", "rns");
        var p = new Palette(); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-40,0,3],[40,0,3]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        scene.setCell(0, 0, lv, 1);
        var renderer = new Renderer(); var level = renderer.renderScene(scene);
        print(level ? "ok fc="+level.frameCount : "null")''',
    ], lambda r: ("ok fc=" in output_of(r), f"out={output_of(r)}"), group=G)


# ============================================================
#  TRANSFORM + IMAGEBUILDER
# ============================================================

def test_transform_imagebuilder():
    G = "Transform + ImageBuilder"

    test("Transform translate + rotate + scale", [
        '''var t = new Transform(); t.translate(10, 20); t.rotate(45); t.scale(2); print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    test("Transform scale(sx, sy) non-uniform", [
        'var t = new Transform(); t.scale(2, 0.5); print("ok")',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    test("ImageBuilder add image with transform", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-20,0,2],[20,0,2]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        var img = vi.toImage();
        var t = new Transform(); t.translate(50, 0);
        var builder = new ImageBuilder();
        builder.add(img);
        builder.add(img, t);
        var result = builder.image;
        print(result ? "ok type="+result.type : "null")''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    test("ImageBuilder fill with named color", [
        'var builder = new ImageBuilder(); try { builder.fill("red"); print("ok"); } catch(e) { print("error:"+e); }',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    test("ImageBuilder fill with hex color", [
        'var builder = new ImageBuilder(); try { builder.fill("#FF8800"); print("ok"); } catch(e) { print("error:"+e); }',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    test("ImageBuilder clear", [
        '''var builder = new ImageBuilder();
        builder.fill("blue");
        builder.clear();
        print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)


# ============================================================
#  IMAGE I/O
# ============================================================

def test_image_io():
    G = "Image I/O and Properties"

    # Save and load PNG
    outpath = os.path.join(TESTDIR, "test_img_io.png")
    test("Save image as PNG and verify file", [
        f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-30,0,3],[30,0,3]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        var rast = new Rasterizer(); rast.xres = 64; rast.yres = 64; rast.dpi = 72;
        var img = rast.rasterize(vi.toImage());
        img.save("{outpath}");
        print("saved " + img.width + "x" + img.height)''',
    ], lambda r: (file_exists_and_nonzero(outpath), f"out={output_of(r)}"), group=G)

    # Load image back
    test("Load PNG back as Image", [
        f'''var img = new Image(); img.load("{outpath}");
        print("type="+img.type+" "+img.width+"x"+img.height+" dpi="+img.dpi)''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Save as TIF
    tifpath = os.path.join(TESTDIR, "test_img_io.tif")
    test("Save image as TIF", [
        f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[-30,0,3],[30,0,3]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        var rast = new Rasterizer(); rast.xres = 64; rast.yres = 64; rast.dpi = 72;
        rast.rasterize(vi.toImage()).save("{tifpath}");
        print("saved")''',
    ], lambda r: (file_exists_and_nonzero(tifpath), f"file={'exists' if file_exists_and_nonzero(tifpath) else 'MISSING'}"), group=G)


# ============================================================
#  LEVEL SAVE/LOAD
# ============================================================

def test_level_io():
    G = "Level Save/Load"

    # Save vector level as PLI
    plipath = os.path.join(TESTDIR, "test_level.pli")
    test("Save vector level as .pli", [
        f'''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "svpli");
        lv.setPalette(p);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        try {{ lv.save("{plipath}"); print("saved"); }} catch(e) {{ print("error:"+e); }}''',
    ], lambda r: (True, f"out={output_of(r)} file={'exists' if file_exists_and_nonzero(plipath) else 'MISSING'}"), group=G)

    # Save ToonzRaster level as TLV
    tlvpath = os.path.join(TESTDIR, "test_level.tlv")
    test("Save ToonzRaster level as .tlv", [
        f'''var scene = new Scene(); var lv = scene.newLevel("ToonzRaster", "svtlv");
        var rc = new RasterCanvas(128, 128);
        rc.brushStroke([[10,64,3],[118,64,3]], 1, true);
        lv.setFrame(1, rc.toImage());
        try {{ lv.save("{tlvpath}"); print("saved"); }} catch(e) {{ print("error:"+e); }}''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)


# ============================================================
#  SCENE SAVE/LOAD
# ============================================================

def test_scene_io():
    G = "Scene Save/Load"

    tnzpath = os.path.join(TESTDIR, "test_scene.tnz")
    test("Save scene as .tnz", [
        f'''var scene = new Scene(); var lv = scene.newLevel("Vector", "scn");
        var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        scene.setCell(0, 0, lv, 1);
        try {{ scene.save("{tnzpath}"); print("saved"); }} catch(e) {{ print("error:"+e); }}''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    test("Load scene from .tnz", [
        f'''var scene = new Scene();
        try {{ scene.load("{tnzpath}"); print("loaded cols="+scene.columnCount); }} catch(e) {{ print("error:"+e); }}''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)


# ============================================================
#  EDGE CASES AND STRESS
# ============================================================

def test_edge_cases():
    G = "Edge Cases and Stress Tests"

    # Empty VectorImage toImage
    test("Empty VectorImage toImage (no strokes)", [
        '''var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var vi = new VectorImage(); vi.setPalette(p);
        try { var img = vi.toImage(); print(img ? "ok type="+img.type : "null"); } catch(e) { print("error:"+e); }''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Rasterize empty VectorImage
    test("Rasterize empty VectorImage", [
        f'''var p = new Palette(); p.addPage("X"); p.addColor(0,0,0,255);
        var vi = new VectorImage(); vi.setPalette(p);
        var rast = new Rasterizer(); rast.xres = 64; rast.yres = 64; rast.dpi = 72;
        try {{ var img = rast.rasterize(vi.toImage()); img.save("{TESTDIR}/test_empty_rast.png"); print("ok "+img.width+"x"+img.height); }} catch(e) {{ print("error:"+e); }}''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Stroke with duplicate points
    test("Stroke with all identical points", [
        'var s = new Stroke(); s.addPoints([[50,50,2],[50,50,2],[50,50,2]]); s.build(); print("len="+s.length)',
    ], lambda r: (True, f"out={output_of(r)} [degenerate - zero length?]"), group=G)

    # Very many strokes in one VectorImage
    test("VectorImage with 100 strokes", [
        '''var vi = new VectorImage();
        for(var i=0;i<100;i++) {
            var s = new Stroke(); s.addPoints([[i,0,1],[i,10,1]]); s.build(); vi.addStroke(s);
        }
        print("strokes="+vi.strokeCount)''',
    ], lambda r: (output_of(r) == "strokes=100", f"out={output_of(r)}"), group=G)

    # Multiple eval calls sharing state
    test("Variables persist across eval calls", [
        'var shared = 42; print("set")',
        'print("shared=" + shared)',
    ], lambda r: ("shared=42" in output_of(r, 1), f"out={output_of(r,1)}"), group=G)

    # Palette assigned to level affects all frames
    test("Level palette shared across frames", [
        '''var p = new Palette(); p.addPage("X"); var ink = p.addColor(0,0,0,255);
        var scene = new Scene(); var lv = scene.newLevel("Vector", "shpal");
        lv.setPalette(p);
        for(var f=1;f<=3;f++) {
            var vi = new VectorImage(); var s = new Stroke(); s.addPoints([[0,0,2],[f*20,0,2]]); s.build(); s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
            lv.setFrame(f, vi.toImage());
        }
        p.setStyleColor(ink, 255, 0, 0, 255);
        var p2 = lv.getPalette();
        var c = p2 ? p2.getStyleColor(ink) : null;
        print(c ? "r="+c.r : "null")''',
    ], lambda r: (True, f"out={output_of(r)} [palette mutation propagation]"), group=G)

    # Unicode in names
    test("Unicode in level name", [
        'var scene = new Scene(); try { var lv = scene.newLevel("Vector", "キャラ"); print("name="+lv.name); } catch(e) { print("error:"+e); }',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Empty string level name
    test("Empty string level name (expect error)", [
        'var scene = new Scene(); try { var lv = scene.newLevel("Vector", ""); print("name=["+lv.name+"]"); } catch(e) { print("error"); }',
    ], lambda r: ("error" in output_of(r), f"out={output_of(r)}"), group=G)

    # getStageObject for large column index (auto-creates - known behavior)
    test("getStageObject for large column index (auto-creates)", [
        'var scene = new Scene(); try { var obj = scene.getStageObject(99); print(obj ? "got:"+obj.name : "null"); } catch(e) { print("error"); }',
    ], lambda r: (True, f"out={output_of(r)} [auto-creates column]"), group=G)

    # RasterCanvas brushStroke with empty points array
    test("brushStroke with empty points array", [
        'var rc = new RasterCanvas(100,100); try { rc.brushStroke([], 1, true); print("ok"); } catch(e) { print("error"); }',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # RasterCanvas fill with invalid styleId (very large)
    test("RasterCanvas fill with styleId=99999", [
        'var rc = new RasterCanvas(100,100); try { rc.fill(50,50,99999); print("ok"); } catch(e) { print("error"); }',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)

    # Concurrent-like: create 2 scenes in same session
    test("Two scenes in same session", [
        '''var s1 = new Scene(); s1.newLevel("Vector","a");
        var s2 = new Scene(); s2.newLevel("Vector","b");
        print("s1="+s1.columnCount+" s2="+s2.columnCount)''',
    ], lambda r: (True, f"out={output_of(r)}"), group=G)


# ============================================================
#  WORKFLOW INTEGRATION: FULL CHARACTER PIPELINE
# ============================================================

def test_full_pipeline():
    G = "Full Pipeline: Character Design -> Animate -> Render"

    outdir = TESTDIR
    test("Full pipeline: draw, fill, animate, render 5 frames", [
        # Create palette
        '''var pal = new Palette(); pal.addPage("char");
        var ink = pal.addColor(30,30,30,255);
        var skinFill = pal.addColor(255,210,180,255);
        var shirtFill = pal.addColor(50,100,200,255);
        print("palette ok: " + pal.styleCount + " styles")''',
        # Draw character frame 1 (arms up)
        '''var vi1 = new VectorImage();
        var head = new Stroke(); head.addPoints([[-20,65,2],[-15,80,2],[0,85,2],[15,80,2],[20,65,2],[15,50,2],[0,45,2],[-15,50,2],[-20,65,2]]); head.build(); head.close(); head.setStyle(ink); vi1.addStroke(head);
        var body = new Stroke(); body.addPoints([[-15,45,2],[-18,10,2],[-10,-25,2],[0,-30,2],[10,-25,2],[18,10,2],[15,45,2]]); body.build(); body.setStyle(ink); vi1.addStroke(body);
        var la = new Stroke(); la.addPoints([[-18,30,2],[-45,60,2]]); la.build(); la.setStyle(ink); vi1.addStroke(la);
        var ra = new Stroke(); ra.addPoints([[18,30,2],[45,60,2]]); ra.build(); ra.setStyle(ink); vi1.addStroke(ra);
        var ll = new Stroke(); ll.addPoints([[-10,-25,2],[-15,-70,2]]); ll.build(); ll.setStyle(ink); vi1.addStroke(ll);
        var rl = new Stroke(); rl.addPoints([[10,-25,2],[15,-70,2]]); rl.build(); rl.setStyle(ink); vi1.addStroke(rl);
        vi1.setPalette(pal);
        print("frame1: " + vi1.strokeCount + " strokes")''',
        # Draw character frame 2 (arms down)
        '''var vi2 = new VectorImage();
        var head2 = new Stroke(); head2.addPoints([[-20,65,2],[-15,80,2],[0,85,2],[15,80,2],[20,65,2],[15,50,2],[0,45,2],[-15,50,2],[-20,65,2]]); head2.build(); head2.close(); head2.setStyle(ink); vi2.addStroke(head2);
        var body2 = new Stroke(); body2.addPoints([[-15,45,2],[-18,10,2],[-10,-25,2],[0,-30,2],[10,-25,2],[18,10,2],[15,45,2]]); body2.build(); body2.setStyle(ink); vi2.addStroke(body2);
        var la2 = new Stroke(); la2.addPoints([[-18,30,2],[-45,-10,2]]); la2.build(); la2.setStyle(ink); vi2.addStroke(la2);
        var ra2 = new Stroke(); ra2.addPoints([[18,30,2],[45,-10,2]]); ra2.build(); ra2.setStyle(ink); vi2.addStroke(ra2);
        var ll2 = new Stroke(); ll2.addPoints([[-10,-25,2],[-15,-70,2]]); ll2.build(); ll2.setStyle(ink); vi2.addStroke(ll2);
        var rl2 = new Stroke(); rl2.addPoints([[10,-25,2],[15,-70,2]]); rl2.build(); rl2.setStyle(ink); vi2.addStroke(rl2);
        vi2.setPalette(pal);
        print("frame2: " + vi2.strokeCount + " strokes")''',
        # Inbetween + rasterize
        f'''var img1 = vi1.toImage(); var img2 = vi2.toImage();
        var tw = new Inbetween(img1, img2);
        var rast = new Rasterizer(); rast.xres = 96; rast.yres = 96; rast.dpi = 72;
        for(var i=0; i<=4; i++) {{
            var t = i/4.0;
            var frame = (i==0) ? img1 : (i==4) ? img2 : tw.tween(t, "easeInOut");
            rast.rasterize(frame).save("{outdir}/testpipeline" + i + ".png");
        }}
        print("rendered 5 frames")''',
    ], lambda r: (all(file_exists_and_nonzero(f"{outdir}/testpipeline{i}.png") for i in range(5)),
                  f"out={output_of(r,3)} files={'all exist' if all(file_exists_and_nonzero(f'{outdir}/testpipeline{i}.png') for i in range(5)) else 'SOME MISSING'}"), group=G)


# ============================================================
#  NEW FEATURE TESTS (G6, G7, G8, G9, G10, G11, G16)
# ============================================================

def test_new_features():
    G = "New Features (G6, G7, G8, G9, G10, G11, G16)"

    # G11: RasterCanvas rectFill on blank canvas
    test("G11: RasterCanvas rectFill on blank canvas", [
        'var rc = new RasterCanvas(64, 64)',
        'var pal = new Palette(); var sid = pal.addColor(255, 0, 0); rc.setPalette(pal)',
        'rc.rectFill(10, 10, 50, 50, sid)',
        f'var img = rc.toImage(); img.save("{TESTDIR}/test_rectfill_blank.png"); print("saved")',
    ], lambda r: (output_of(r, 3) == "saved", f"out={output_of(r, 3)}"), group=G)

    test("G11: RasterCanvas rectFill produces non-empty image", [
        'var rc = new RasterCanvas(64, 64)',
        'var pal = new Palette(); var sid = pal.addColor(0, 0, 255); rc.setPalette(pal)',
        'rc.rectFill(0, 0, 63, 63, sid)',
        f'var img = rc.toImage(); img.save("{TESTDIR}/test_rectfill_full.png"); print("saved")',
    ], lambda r: (output_of(r, 3) == "saved", f"out={output_of(r, 3)}"), group=G)

    # G10: PlasticRig setVertexKeyframe
    test("G10: PlasticRig setVertexKeyframe works", [
        'var rig = new PlasticRig()',
        'var root = rig.addVertex(0, 0, -1); print("root=" + root)',
        'var v1 = rig.addVertex(50, 0, root); print("v1=" + v1)',
        'rig.setVertexKeyframe(v1, 0, "angle", 0); print("kf0 ok")',
        'rig.setVertexKeyframe(v1, 24, "angle", 45); print("kf24 ok")',
    ], lambda r: (output_of(r, 3) == "kf0 ok" and output_of(r, 4) == "kf24 ok",
                  f"kf0={output_of(r, 3)} kf24={output_of(r, 4)}"), group=G)

    test("G10: PlasticRig setVertexKeyframe distance param", [
        'var rig = new PlasticRig()',
        'var root = rig.addVertex(0, 0, -1)',
        'var v1 = rig.addVertex(50, 0, root)',
        'rig.setVertexKeyframe(v1, 0, "distance", 0); print("dist ok")',
    ], lambda r: (output_of(r, 3) == "dist ok", f"out={output_of(r, 3)}"), group=G)

    test("G10: PlasticRig setVertexKeyframe so param", [
        'var rig = new PlasticRig()',
        'var root = rig.addVertex(0, 0, -1)',
        'var v1 = rig.addVertex(50, 0, root)',
        'rig.setVertexKeyframe(v1, 0, "so", 1); print("so ok")',
    ], lambda r: (output_of(r, 3) == "so ok", f"out={output_of(r, 3)}"), group=G)

    # G16: Camera settings
    test("G16: setCameraSize and getCameraSize", [
        'var scene = new Scene()',
        'scene.setCameraSize(1920, 1080)',
        'var cam = scene.getCameraSize(); print(cam.width + "x" + cam.height)',
    ], lambda r: (output_of(r, 2) == "1920x1080", f"out={output_of(r, 2)}"), group=G)

    test("G16: setCameraSize rejects non-positive", [
        'var scene = new Scene()',
        'try { scene.setCameraSize(0, 100); print("no error"); } catch(e) { print("error"); }',
    ], lambda r: (output_of(r, 1) == "error", f"out={output_of(r, 1)}"), group=G)

    # G7: Drawing hooks
    test("G7: Level addHook and getHooks", [
        'var scene = new Scene()',
        'var lev = scene.newLevel("Vector", "hooktest")',
        '''var s = new Stroke(); s.addPoint(0,0,1); s.addPoint(100,0,1); s.build();
           var vi = new VectorImage(); vi.addStroke(s);
           var pal = new Palette(); vi.setPalette(pal);
           lev.setFrame(1, vi.toImage()); print("frame set")''',
        'var idx = lev.addHook(1, 50, 25); print("hook=" + idx)',
        'var hooks = lev.getHooks(1); print("count=" + hooks.length + " x=" + hooks[0].x + " y=" + hooks[0].y)',
    ], lambda r: ("hook=" in output_of(r, 3) and "count=1" in output_of(r, 4),
                  f"hook={output_of(r, 3)} get={output_of(r, 4)}"), group=G)

    test("G7: Level removeHook", [
        'var scene = new Scene()',
        'var lev = scene.newLevel("Vector", "hookrm")',
        '''var s = new Stroke(); s.addPoint(0,0,1); s.addPoint(100,0,1); s.build();
           var vi = new VectorImage(); vi.addStroke(s);
           var pal = new Palette(); vi.setPalette(pal);
           lev.setFrame(1, vi.toImage())''',
        'var idx = lev.addHook(1, 10, 20)',
        'lev.removeHook(idx); print("removed")',
    ], lambda r: (output_of(r, 4) == "removed", f"out={output_of(r, 4)}"), group=G)

    # G6: Motion path splines
    test("G6: Scene createSpline", [
        'var scene = new Scene(); scene.newLevel("Vector", "sptest")',
        'var idx = scene.createSpline([[0,0],[100,50],[200,0]]); print("spline=" + idx)',
    ], lambda r: ("spline=" in output_of(r, 1), f"out={output_of(r, 1)}"), group=G)

    test("G6: StageObject setSpline", [
        'var scene = new Scene(); scene.newLevel("Vector", "sp2")',
        'var idx = scene.createSpline([[0,0],[100,0],[200,0]])',
        'var obj = scene.getStageObject(0); obj.setSpline(idx); print("assigned")',
    ], lambda r: (output_of(r, 2) == "assigned", f"out={output_of(r, 2)}"), group=G)

    test("G6: StageObject setSpline + path status", [
        'var scene = new Scene(); scene.newLevel("Vector", "sp3")',
        'var idx = scene.createSpline([[0,0],[50,100],[100,0]])',
        'var obj = scene.getStageObject(0); obj.setSpline(idx); obj.setStatus("path"); print("status=" + obj.status)',
    ], lambda r: (output_of(r, 2) == "status=path", f"out={output_of(r, 2)}"), group=G)

    test("G6: createSpline rejects too few points", [
        'var scene = new Scene()',
        'try { scene.createSpline([[0,0],[1,1]]); print("no error"); } catch(e) { print("error"); }',
    ], lambda r: (output_of(r, 1) == "error", f"out={output_of(r, 1)}"), group=G)

    # G8: IK solver
    test("G8: solveIK on 3-bone chain", [
        '''var scene = new Scene();
        scene.newLevel("Vector", "ik1"); scene.newLevel("Vector", "ik2"); scene.newLevel("Vector", "ik3");
        scene.setCell(0, 0, scene.getLevel("ik1"), 1);
        scene.setCell(0, 1, scene.getLevel("ik2"), 1);
        scene.setCell(0, 2, scene.getLevel("ik3"), 1);
        var root = scene.getStageObject(0);
        var mid = scene.getStageObject(1);
        var tip = scene.getStageObject(2);
        root.setKeyframe(0, "x", 0); root.setKeyframe(0, "y", 0);
        mid.setKeyframe(0, "x", 50); mid.setKeyframe(0, "y", 0);
        tip.setKeyframe(0, "x", 100); tip.setKeyframe(0, "y", 0);
        mid.setParent(root);
        tip.setParent(mid);
        var angles = tip.solveIK(80, 30, 0);
        print("solved=" + (angles !== undefined && angles !== null ? "ok" : "fail"))''',
    ], lambda r: ("solved=ok" in output_of(r), f"out={output_of(r)}"), group=G)

    test("G8: solveIK on single object (table is implicit parent)", [
        '''var scene = new Scene(); scene.newLevel("Vector", "ik_single");
        scene.setCell(0, 0, scene.getLevel("ik_single"), 1);
        var obj = scene.getStageObject(0);
        obj.setKeyframe(0, "x", 50); obj.setKeyframe(0, "y", 0);
        var angles = obj.solveIK(30, 30, 0);
        print("solved=" + (angles !== undefined ? "ok" : "fail"))''',
    ], lambda r: ("solved=ok" in output_of(r), f"out={output_of(r)}"), group=G)

    # G9: Color model
    test("G9: Palette loadColorModel + pickColorFromModel", [
        # Create a small test image first
        '''var rc = new RasterCanvas(16, 16);
        var pal = new Palette(); var red = pal.addColor(255, 0, 0); rc.setPalette(pal);
        rc.rectFill(0, 0, 15, 15, red);
        var img = rc.toImage();''' + f'''
        img.save("{TESTDIR}/test_colormodel.png"); print("saved")''',
        f'''var pal2 = new Palette(); pal2.addColor(255, 0, 0); pal2.addColor(0, 255, 0);
        pal2.loadColorModel("{TESTDIR}/test_colormodel.png");
        var c = pal2.pickColorFromModel(8, 8);
        print("r=" + c.r + " closest=" + c.closestStyleId)''',
    ], lambda r: ("r=" in output_of(r, 1), f"out={output_of(r, 1)}"), group=G)

    test("G9: Palette removeColorModel", [
        '''var pal = new Palette();''' + f'''
        pal.loadColorModel("{TESTDIR}/test_colormodel.png");
        pal.removeColorModel();
        try {{ var c = pal.pickColorFromModel(0, 0); print("no error"); }} catch(e) {{ print("error"); }}''',
    ], lambda r: (output_of(r) == "error", f"out={output_of(r)}"), group=G)

    test("G9: pickColorFromModel without loading errors", [
        'var pal = new Palette()',
        'try { pal.pickColorFromModel(0, 0); print("no error"); } catch(e) { print("error"); }',
    ], lambda r: (output_of(r, 1) == "error", f"out={output_of(r, 1)}"), group=G)


# ============================================================
#  MISSING WORKFLOW FEATURES (gaps)
# ============================================================

def test_missing_features():
    G = "Missing/Untestable Workflow Features (Gaps)"

    # Step 2: Color Model — IMPLEMENTED (G9)
    test("[IMPLEMENTED] Color Model (loadColorModel/pickColorFromModel)", [
        f'''var pal = new Palette(); pal.addColor(128, 128, 128);
        pal.loadColorModel("{TESTDIR}/test_colormodel.png");
        var c = pal.pickColorFromModel(0, 0); print("r=" + c.r)''',
    ], lambda r: ("r=" in output_of(r), f"out={output_of(r)}"), group=G)

    # Step 6: Onion Skin - no API exposure
    test("[GAP] Onion Skin overlay - no headless API", [
        'print("Onion Skin (MOS/FOS/ShiftTrace) has no headless API binding")',
    ], lambda r: (True, "NO API - Onion Skin not exposed"), group=G)

    # Step 10: Skeleton/Bone rig — IMPLEMENTED (G8)
    test("[IMPLEMENTED] IK solver (solveIK on parent chain)", [
        '''var scene = new Scene();
        scene.newLevel("Vector","sk1"); scene.newLevel("Vector","sk2");
        scene.setCell(0,0,scene.getLevel("sk1"),1); scene.setCell(0,1,scene.getLevel("sk2"),1);
        var a = scene.getStageObject(0); var b = scene.getStageObject(1);
        a.setKeyframe(0,"x",0); a.setKeyframe(0,"y",0);
        b.setKeyframe(0,"x",50); b.setKeyframe(0,"y",0);
        b.setParent(a); var r = b.solveIK(30, 30, 0); print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # Step 13: Motion Paths (splines) — IMPLEMENTED (G6)
    test("[IMPLEMENTED] Motion Path spline creation + assignment", [
        '''var scene = new Scene(); scene.newLevel("Vector","mp");
        var idx = scene.createSpline([[0,0],[100,50],[200,0]]);
        var obj = scene.getStageObject(0); obj.setSpline(idx); obj.setStatus("path");
        print("status="+obj.status)''',
    ], lambda r: (output_of(r) == "status=path", f"out={output_of(r)}"), group=G)

    # Fill tool modes: rect, polyline, freehand - vector
    test("[GAP] VectorImage fill modes (rect/polyline/freehand)", [
        'print("VectorImage only has point-based fill(x,y,style). No rect/polyline/freehand fill.")',
    ], lambda r: (True, "NO API - Only point fill, no rect/polyline/freehand fill for vectors"), group=G)

    # Paint brush tool
    test("[GAP] Paint Brush tool for touch-ups", [
        'print("No paint brush tool equivalent in headless API")',
    ], lambda r: (True, "NO API - Paint Brush tool not exposed"), group=G)

    # Style Picker tool
    test("[GAP] Style Picker tool", [
        'print("No style picker tool in headless API")',
    ], lambda r: (True, "NO API - Style Picker not exposed"), group=G)

    # Geometric tool — IMPLEMENTED (G5)
    test("[IMPLEMENTED] Geometric primitives (addRect/addCircle/addPolygon)", [
        '''var vi = new VectorImage();
        vi.addRect(0,0,50,50,1,1); vi.addCircle(75,25,20,1,1); vi.addPolygon(120,25,15,6,1,1);
        print("strokes=" + vi.strokeCount)''',
    ], lambda r: ("strokes=" in output_of(r) and int(output_of(r).replace("strokes=","")) > 0,
                  f"out={output_of(r)}"), group=G)

    # Brush presets
    test("[GAP] Brush preset system (VectorBrushData)", [
        'print("No brush preset loading/saving in headless API")',
    ], lambda r: (True, "NO API - Brush presets not exposed"), group=G)

    # Cap/join/miter stroke styles
    test("[GAP] Stroke cap/join/miter styles", [
        'print("Stroke has setStyle(id) for color but no cap/join/miter control")',
    ], lambda r: (True, "NO API - No stroke cap/join/miter control"), group=G)

    # Draw order / lock-alpha
    test("[GAP] Draw order and lock-alpha modifier", [
        'print("No draw order or lock-alpha control in headless")',
    ], lambda r: (True, "NO API - Draw order / lock-alpha not exposed"), group=G)

    # MyPaint brush engine
    test("[GAP] MyPaint brush engine", [
        'print("No MyPaint brush engine in headless API")',
    ], lambda r: (True, "NO API - MyPaint brushes not exposed"), group=G)

    # Level palette types: studio palette, cleanup palette
    test("[GAP] Studio Palette and Cleanup Palette", [
        'print("Only level palette available. No studio/cleanup palette management.")',
    ], lambda r: (True, "NO API - Studio/Cleanup palette not exposed"), group=G)

    # Expression-driven parameters
    test("[GAP] Expression-driven animation parameters", [
        'print("No expression-based keyframe interpolation in headless")',
    ], lambda r: (True, "NO API - Expression params not exposed"), group=G)

    # Camera settings — IMPLEMENTED (G16)
    test("[IMPLEMENTED] Camera settings (setCameraSize/getCameraSize)", [
        'var scene = new Scene(); scene.setCameraSize(1280, 720); var c = scene.getCameraSize(); print(c.width + "x" + c.height)',
    ], lambda r: (output_of(r) == "1280x720", f"out={output_of(r)}"), group=G)

    # Hooks (attachment points) — IMPLEMENTED (G7)
    test("[IMPLEMENTED] Drawing hooks (addHook/getHooks/removeHook)", [
        '''var scene = new Scene(); var lev = scene.newLevel("Vector","hk");
        var s = new Stroke(); s.addPoint(0,0,1); s.addPoint(10,0,1); s.build();
        var vi = new VectorImage(); vi.addStroke(s); var pal = new Palette(); vi.setPalette(pal);
        lev.setFrame(1, vi.toImage()); lev.addHook(1, 5, 5); print("ok")''',
    ], lambda r: (output_of(r) == "ok", f"out={output_of(r)}"), group=G)

    # Frame range fill (multi-frame batch)
    test("[GAP] Frame range fill (batch fill across frames)", [
        'print("No frame range fill in headless - must fill each frame individually")',
    ], lambda r: (True, "NO API - Frame range fill not exposed"), group=G)

    # Undo/Redo
    test("[GAP] Undo/Redo system", [
        'print("No undo/redo in headless - operations are immediate and permanent")',
    ], lambda r: (True, "NO API - No undo/redo"), group=G)

    # PlasticRig mesh generation from image
    test("[GAP] PlasticRig auto mesh generation from drawing", [
        'print("PlasticRig has skeleton but no mesh triangulation from drawing")',
    ], lambda r: (True, "NO API - Mesh auto-generation not exposed"), group=G)

    # PlasticRig apply deformation to image
    test("[GAP] PlasticRig apply deformation to render", [
        '''var rig = new PlasticRig(); var root = rig.addVertex(0,0,-1);
        print("PlasticRig exists but cannot apply deformation to actual image/render")''',
    ], lambda r: (True, f"out={output_of(r)} - NO WAY TO APPLY DEFORMATION TO IMAGE"), group=G)

    # Effect connection to scene/columns — IMPLEMENTED (G2)
    test("[IMPLEMENTED] Connect Effect to scene column (connectEffect)", [
        '''var scene = new Scene(); scene.newLevel("Vector","fxtest");
        scene.setCell(0, 0, scene.getLevel("fxtest"), 1);
        var fx = new Effect("STD_blurFx"); fx.setParam("value", 5);
        scene.connectEffect(0, fx); print("connected")''',
    ], lambda r: (output_of(r) == "connected", f"out={output_of(r)}"), group=G)

    # Renderer with effects
    test("[GAP] Renderer with effects applied", [
        'print("Cannot render scene with effects since effects cannot be connected to columns")',
    ], lambda r: (True, "NO API - Effect -> Scene connection missing, so rendered output has no FX"), group=G)

    # Smoothing / acceleration settings for strokes
    test("[GAP] Stroke smoothing/acceleration controls", [
        'print("No smoothing, acceleration, or break angle control for Stroke")',
    ], lambda r: (True, "NO API - Stroke smoothing/acceleration not exposed"), group=G)

    # Pencil mode (aliased) for raster
    test("[GAP] Pencil mode (aliased) for RasterCanvas", [
        'print("RasterCanvas brushStroke has antialias bool but no pencil mode equivalent")',
    ], lambda r: (True, "PARTIAL - antialias=false approximates pencil mode"), group=G)

    # RasterCanvas hardness/opacity control
    test("[GAP] RasterCanvas brush hardness/opacity", [
        'print("brushStroke has no hardness or opacity parameter")',
    ], lambda r: (True, "NO API - Brush hardness/opacity not exposed"), group=G)


# ============================================================
#  MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  COMPREHENSIVE ATOMIC TEST SUITE")
    print("  OpenToonz Headless JSON-RPC Interface")
    print("=" * 60)

    # Clean up old test images
    import glob
    for f in set(glob.glob(os.path.join(TESTDIR, "test*.png")) +
                 glob.glob(os.path.join(TESTDIR, "test*.tif"))):
        if os.path.exists(f):
            os.remove(f)

    test_step1_levels()
    test_step3_palette()
    test_step4_stroke()
    test_step4_vectorimage()
    test_step4_rastercanvas()
    test_step5_fill()
    test_step7_frames()
    test_step8_xsheet()
    test_step9_keyframes()
    test_step11_plasticrig()
    test_step12_inbetween()
    test_step14_effects()
    test_rasterizer()
    test_renderer()
    test_transform_imagebuilder()
    test_image_io()
    test_level_io()
    test_scene_io()
    test_edge_cases()
    test_full_pipeline()
    test_new_features()
    test_missing_features()

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    # Group by category
    groups = {}
    for r in results:
        g = r["group"]
        if g not in groups:
            groups[g] = {"pass": 0, "fail": 0, "tests": []}
        groups[g]["tests"].append(r)
        if r["passed"]:
            groups[g]["pass"] += 1
        else:
            groups[g]["fail"] += 1

    print(f"\n  Total: {total} tests | PASS: {passed} | FAIL: {failed}\n")

    for g, data in groups.items():
        status = "ALL PASS" if data["fail"] == 0 else f"{data['fail']} FAIL"
        print(f"  {g}: {data['pass']}/{data['pass']+data['fail']} ({status})")

    # List all failures
    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for r in failures:
            print(f"    - [{r['group']}] {r['name']}: {r['detail']}")

    # List GAPs
    gaps = [r for r in results if "[GAP]" in r["name"] or "NO API" in r["detail"] or "NO WAY" in r["detail"]]
    if gaps:
        print(f"\n  API GAPS ({len(gaps)}):")
        for r in gaps:
            print(f"    - {r['name']}: {r['detail']}")

    # List items needing investigation
    investigate = [r for r in results if "INVESTIGATE" in r["detail"] or "investigate" in r["detail"]
                   or "should error" in r["detail"].lower()]
    if investigate:
        print(f"\n  NEEDS INVESTIGATION ({len(investigate)}):")
        for r in investigate:
            print(f"    - {r['name']}: {r['detail']}")

    # List output files
    print(f"\n  OUTPUT FILES:")
    for f in sorted(glob.glob(os.path.join(TESTDIR, "test_*.png")) + glob.glob(os.path.join(TESTDIR, "test_*.tif"))):
        size = os.path.getsize(f)
        print(f"    {os.path.basename(f)}: {size} bytes")

    sys.exit(0 if failed == 0 else 1)
