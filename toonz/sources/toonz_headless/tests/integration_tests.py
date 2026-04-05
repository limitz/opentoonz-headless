#!/usr/bin/env python3
"""
Integration test suite for OpenToonz Headless — multi-step pipelines.
Tests end-to-end workflows that combine multiple API features.
"""

import subprocess
import json
import os
import sys
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
HEADLESS = os.environ.get("TOONZ_HEADLESS", os.path.join(PROJECT_ROOT, "toonz", "sources", "build", "bin", "toonz_headless"))
TESTDIR = os.environ.get("TOONZ_TEST_OUTPUT", "/tmp/toonz_headless_integration")
os.makedirs(TESTDIR, exist_ok=True)
if "TOONZROOT" not in os.environ:
    os.environ["TOONZROOT"] = os.path.join(PROJECT_ROOT, "stuff")

results = []
current_group = ""


def run_session(commands, timeout=30):
    """Run a list of JS code strings in a single headless session."""
    lines = []
    for i, code in enumerate(commands):
        msg = json.dumps({"id": i+1, "method": "eval", "params": {"code": code}})
        lines.append(msg)
    lines.append(json.dumps({"id": 9999, "method": "quit", "params": {}}))
    stdin_data = "\n".join(lines) + "\n"

    proc = subprocess.run(
        [HEADLESS],
        input=stdin_data, capture_output=True, text=True, timeout=timeout
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

    icon = "  OK" if passed else "FAIL"
    print(f"  [{icon}] {name}: {detail}")
    results.append({"name": name, "group": current_group, "passed": passed, "detail": detail})
    return passed


def output_of(responses, idx=0):
    _, resp = responses[idx]
    if resp and "result" in resp:
        return resp["result"].get("output", "")
    return ""


def has_error(responses, idx=0):
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
#  PLASTIC DEFORMATION PIPELINE
# ============================================================

def test_plastic_deformation():
    G = "Plastic Deformation Pipeline"

    # scene.buildMesh: basic mesh generation from raster + render
    outpath_bm = os.path.join(TESTDIR, "test_buildmesh_basic.png")
    test("buildMesh from Raster image", [
        f'''var scene = new Scene(); scene.setCameraSize(64, 64);
        var lv = scene.newLevel("ToonzRaster", "bm_src");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[8,8,3],[56,8,3],[56,56,3],[8,56,3],[8,8,3]], 1, true);
        lv.setFrame(1, rc.toImage());
        scene.setCell(0, 0, lv, 1);
        var texImg = lv.getFrame(1);
        var meshLevel = scene.buildMesh(texImg, "bm_mesh");
        scene.setCell(0, 1, meshLevel, 1);
        var texObj = scene.getStageObject(0); var meshObj = scene.getStageObject(1);
        texObj.setParent(meshObj);
        var rig = new PlasticRig(); rig.addVertex(0, 0); rig.addVertex(0, 20, 0);
        rig.setVertexKeyframe(1, 0, "angle", 20);
        meshObj.setPlasticRig(rig);
        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath_bm}");
        print("fc=1 " + img.width + "x" + img.height)''',
    ], lambda r: ("fc=1" in output_of(r) and file_exists_and_nonzero(outpath_bm), f"out={output_of(r)}"), group=G)

    # buildMesh: verify mesh level can be placed in scene
    outpath_sc = os.path.join(TESTDIR, "test_buildmesh_setcell.png")
    test("buildMesh level works with setCell", [
        f'''var scene = new Scene(); scene.setCameraSize(64, 64);
        var lv = scene.newLevel("ToonzRaster", "sc_src");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[10,10,3],[54,10,3],[54,54,3],[10,54,3],[10,10,3]], 1, true);
        lv.setFrame(1, rc.toImage());
        scene.setCell(0, 0, lv, 1);
        var meshLevel = scene.buildMesh(lv.getFrame(1), "sc_mesh");
        scene.setCell(0, 1, meshLevel, 1);
        var texObj = scene.getStageObject(0); var meshObj = scene.getStageObject(1);
        texObj.setParent(meshObj);
        var rig = new PlasticRig(); rig.addVertex(0, 0); rig.addVertex(0, 20, 0);
        meshObj.setPlasticRig(rig);
        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath_sc}");
        print("cols=" + scene.columnCount)''',
    ], lambda r: (output_of(r) == "cols=2" and file_exists_and_nonzero(outpath_sc), f"out={output_of(r)}"), group=G)

    # buildMesh: error on Vector image
    test("buildMesh rejects Vector image", [
        '''var scene = new Scene();
        var p = new Palette(); var ink = p.addColor(0,0,0,255);
        var vi = new VectorImage();
        var s = new Stroke(); s.addPoints([[0,0,2],[50,0,2]]); s.build();
        s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
        try { scene.buildMesh(vi.toImage(), "bad_mesh"); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: (output_of(r) == "error", f"out={output_of(r)}"), group=G)

    # buildMesh: error on duplicate name
    test("buildMesh rejects duplicate level name", [
        '''var scene = new Scene();
        var lv = scene.newLevel("ToonzRaster", "dup_src");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[10,10,3],[54,10,3],[54,54,3],[10,54,3],[10,10,3]], 1, true);
        lv.setFrame(1, rc.toImage());
        var m1 = scene.buildMesh(lv.getFrame(1), "dup_mesh");
        try { var m2 = scene.buildMesh(lv.getFrame(1), "dup_mesh"); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: (output_of(r) == "error", f"out={output_of(r)}"), group=G)

    # buildMesh: error on empty name
    test("buildMesh rejects empty level name", [
        '''var scene = new Scene();
        var lv = scene.newLevel("ToonzRaster", "empty_nm");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[10,10,3],[54,10,3],[54,54,3],[10,54,3],[10,10,3]], 1, true);
        lv.setFrame(1, rc.toImage());
        try { scene.buildMesh(lv.getFrame(1), ""); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: (output_of(r) == "error", f"out={output_of(r)}"), group=G)

    # setPlasticRig: basic attachment + render
    outpath_pr = os.path.join(TESTDIR, "test_setplasticrig.png")
    test("setPlasticRig attaches rig to stage object", [
        f'''var scene = new Scene(); scene.setCameraSize(64, 64);
        var lv = scene.newLevel("ToonzRaster", "pr_src");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[10,10,3],[54,10,3],[54,54,3],[10,54,3],[10,10,3]], 1, true);
        lv.setFrame(1, rc.toImage());
        scene.setCell(0, 0, lv, 1);
        var meshLevel = scene.buildMesh(lv.getFrame(1), "pr_mesh");
        scene.setCell(0, 1, meshLevel, 1);
        var texObj = scene.getStageObject(0); var meshObj = scene.getStageObject(1);
        texObj.setParent(meshObj);
        var rig = new PlasticRig();
        rig.addVertex(0, 0);
        rig.addVertex(0, 20, 0);
        rig.setVertexKeyframe(1, 0, "angle", 15);
        meshObj.setPlasticRig(rig);
        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath_pr}");
        print("ok")''',
    ], lambda r: (output_of(r) == "ok" and file_exists_and_nonzero(outpath_pr), f"out={output_of(r)}"), group=G)

    # setPlasticRig: error on non-rig argument
    test("setPlasticRig rejects non-PlasticRig argument", [
        '''var scene = new Scene();
        scene.newLevel("Vector", "pr_bad");
        var obj = scene.getStageObject(0);
        try { obj.setPlasticRig("not a rig"); print("no_error"); } catch(e) { print("error"); }''',
    ], lambda r: (output_of(r) == "error", f"out={output_of(r)}"), group=G)

    # Full pipeline: wire up and render with plastic deformation
    outpath = os.path.join(TESTDIR, "test_plastic_render.png")
    test("Full plastic deformation pipeline (build + wire + render)", [
        f'''var scene = new Scene();
        scene.setCameraSize(128, 128);

        // Create texture
        var texLevel = scene.newLevel("ToonzRaster", "pd_tex");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[8,8,3],[56,8,3],[56,56,3],[8,56,3],[8,8,3]], 1, true);
        texLevel.setFrame(1, rc.toImage());

        // Fill cells for 25 frames so animation can be rendered
        for (var r = 0; r < 25; r++) {{
            scene.setCell(r, 0, texLevel, 1);
        }}

        // Build mesh from texture
        var texImg = texLevel.getFrame(1);
        var meshLevel = scene.buildMesh(texImg, "pd_mesh");
        for (var r = 0; r < 25; r++) {{
            scene.setCell(r, 1, meshLevel, 1);
        }}

        // Parent texture column to mesh column
        var texObj = scene.getStageObject(0);
        var meshObj = scene.getStageObject(1);
        texObj.setParent(meshObj);

        // Build rig and animate
        var rig = new PlasticRig();
        var root = rig.addVertex(0, 0);
        var tip = rig.addVertex(0, 20, root);
        rig.setVertexKeyframe(tip, 0, "angle", 0);
        rig.setVertexKeyframe(tip, 24, "angle", 45);
        meshObj.setPlasticRig(rig);

        // Render mid-animation frame
        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 12);
        img.save("{outpath}");
        print("rendered type=" + img.type + " " + img.width + "x" + img.height)''',
    ], lambda r: (file_exists_and_nonzero(outpath) and "rendered" in output_of(r),
                  f"out={output_of(r)} file={'exists' if file_exists_and_nonzero(outpath) else 'MISSING'}"), group=G)

    # Render multiple frames to verify animation
    test("Plastic deformation: render 3-frame sequence", [
        f'''var scene = new Scene();
        scene.setCameraSize(64, 64);

        var texLevel = scene.newLevel("ToonzRaster", "seq_tex");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[12,8,3],[52,8,3],[52,56,3],[12,56,3],[12,8,3]], 1, true);
        texLevel.setFrame(1, rc.toImage());
        scene.setCell(0, 0, texLevel, 1);
        scene.setCell(1, 0, texLevel, 1);
        scene.setCell(2, 0, texLevel, 1);

        var meshLevel = scene.buildMesh(texLevel.getFrame(1), "seq_mesh");
        scene.setCell(0, 1, meshLevel, 1);
        scene.setCell(1, 1, meshLevel, 1);
        scene.setCell(2, 1, meshLevel, 1);

        var texObj = scene.getStageObject(0);
        var meshObj = scene.getStageObject(1);
        texObj.setParent(meshObj);

        var rig = new PlasticRig();
        var root = rig.addVertex(0, 0);
        var tip = rig.addVertex(0, 20, root);
        rig.setVertexKeyframe(tip, 0, "angle", 0);
        rig.setVertexKeyframe(tip, 2, "angle", 30);
        meshObj.setPlasticRig(rig);

        var renderer = new Renderer();
        for (var f = 0; f < 3; f++) {{
            var img = renderer.renderFrame(scene, f);
            img.save("{TESTDIR}/test_plastic_seq" + f + ".png");
        }}
        print("rendered 3 frames")''',
    ], lambda r: (all(file_exists_and_nonzero(f"{TESTDIR}/test_plastic_seq{i}.png") for i in range(3)),
                  f"out={output_of(r)} files={'all exist' if all(file_exists_and_nonzero(f'{TESTDIR}/test_plastic_seq{i}.png') for i in range(3)) else 'MISSING'}"), group=G)

    # buildMesh from ToonzRaster
    outpath_tz = os.path.join(TESTDIR, "test_buildmesh_toonzraster.png")
    test("buildMesh from ToonzRaster image", [
        f'''var scene = new Scene(); scene.setCameraSize(64, 64);
        var lv = scene.newLevel("ToonzRaster", "tz_src");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[8,8,3],[56,8,3],[56,56,3],[8,56,3],[8,8,3]], 1, true);
        lv.setFrame(1, rc.toImage());
        scene.setCell(0, 0, lv, 1);
        var meshLevel = scene.buildMesh(lv.getFrame(1), "tz_mesh");
        scene.setCell(0, 1, meshLevel, 1);
        var texObj = scene.getStageObject(0); var meshObj = scene.getStageObject(1);
        texObj.setParent(meshObj);
        var rig = new PlasticRig(); rig.addVertex(0, 0); rig.addVertex(0, 20, 0);
        meshObj.setPlasticRig(rig);
        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath_tz}");
        print("fc=" + meshLevel.frameCount)''',
    ], lambda r: ("fc=1" in output_of(r) and file_exists_and_nonzero(outpath_tz), f"out={output_of(r)}"), group=G)


# ============================================================
#  RENDERER INTEGRATION
# ============================================================

def test_renderer_integration():
    G = "Renderer Integration"

    # Render vector scene
    outpath = os.path.join(TESTDIR, "test_render_vector.png")
    test("Render vector scene to PNG", [
        f'''var scene = new Scene(); scene.setCameraSize(128, 128);
        var lv = scene.newLevel("Vector", "rv");
        var p = new Palette(); var ink = p.addColor(0, 0, 0, 255);
        var vi = new VectorImage();
        vi.addRect(-40, -40, 40, 40, 2, ink);
        vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        scene.setCell(0, 0, lv, 1);
        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath}");
        print("ok " + img.width + "x" + img.height)''',
    ], lambda r: (file_exists_and_nonzero(outpath), f"out={output_of(r)}"), group=G)

    # Render with effects
    outpath_fx = os.path.join(TESTDIR, "test_render_fx.png")
    test("Render scene with blur effect", [
        f'''var scene = new Scene(); scene.setCameraSize(128, 128);
        var lv = scene.newLevel("Vector", "rfx");
        var p = new Palette(); var ink = p.addColor(0, 0, 0, 255);
        var vi = new VectorImage();
        vi.addRect(-30, -30, 30, 30, 3, ink);
        vi.setPalette(p);
        lv.setFrame(1, vi.toImage());
        scene.setCell(0, 0, lv, 1);
        var blur = new Effect("STD_blurFx");
        blur.setParam("value", 15);
        scene.connectEffect(0, blur);
        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath_fx}");
        print("ok " + img.width + "x" + img.height)''',
    ], lambda r: (file_exists_and_nonzero(outpath_fx), f"out={output_of(r)}"), group=G)

    # Render raster scene
    outpath_ras = os.path.join(TESTDIR, "test_render_raster.png")
    test("Render raster scene to PNG", [
        f'''var scene = new Scene(); scene.setCameraSize(64, 64);
        var lv = scene.newLevel("ToonzRaster", "rras");
        var rc = new RasterCanvas(64, 64);
        rc.brushStroke([[10,10,3],[54,10,3],[54,54,3],[10,54,3],[10,10,3]], 1, true);
        lv.setFrame(1, rc.toImage());
        scene.setCell(0, 0, lv, 1);
        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath_ras}");
        print("ok " + img.width + "x" + img.height)''',
    ], lambda r: (file_exists_and_nonzero(outpath_ras), f"out={output_of(r)}"), group=G)

    # renderScene (full level output)
    outpath_rs = os.path.join(TESTDIR, "test_renderscene_frame0.png")
    test("renderScene returns multi-frame level", [
        f'''var scene = new Scene(); scene.setCameraSize(64, 64);
        var lv = scene.newLevel("Vector", "rsl");
        var p = new Palette(); var ink = p.addColor(0, 0, 0, 255);
        for (var f = 1; f <= 3; f++) {{
            var vi = new VectorImage();
            var s = new Stroke(); s.addPoints([[0,0,2],[f*20,0,2]]); s.build();
            s.setStyle(ink); vi.addStroke(s); vi.setPalette(p);
            lv.setFrame(f, vi.toImage());
            scene.setCell(f-1, 0, lv, f);
        }}
        var renderer = new Renderer();
        var outLevel = renderer.renderScene(scene);
        outLevel.getFrameByIndex(0).save("{outpath_rs}");
        print("fc=" + outLevel.frameCount)''',
    ], lambda r: ("fc=3" in output_of(r) and file_exists_and_nonzero(outpath_rs), f"out={output_of(r)}"), group=G)


# ============================================================
#  MULTI-COLUMN SCENE PIPELINE
# ============================================================

def test_multi_column():
    G = "Multi-Column Scene Pipeline"

    # Two columns composited
    outpath = os.path.join(TESTDIR, "test_multicol.png")
    test("Render 2-column scene (composited layers)", [
        f'''var scene = new Scene(); scene.setCameraSize(128, 128);
        var p = new Palette(); var red = p.addColor(255, 0, 0, 255); var blue = p.addColor(0, 0, 255, 255);

        var lv1 = scene.newLevel("Vector", "col0");
        var vi1 = new VectorImage(); vi1.addRect(-40, -40, 0, 0, 2, red); vi1.setPalette(p);
        lv1.setFrame(1, vi1.toImage());
        scene.setCell(0, 0, lv1, 1);

        var lv2 = scene.newLevel("Vector", "col1");
        var vi2 = new VectorImage(); vi2.addRect(0, 0, 40, 40, 2, blue); vi2.setPalette(p);
        lv2.setFrame(1, vi2.toImage());
        scene.setCell(0, 1, lv2, 1);

        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath}");
        print("ok " + img.width + "x" + img.height)''',
    ], lambda r: (file_exists_and_nonzero(outpath), f"out={output_of(r)}"), group=G)

    # Parent-child hierarchy with transforms
    outpath_hier = os.path.join(TESTDIR, "test_hierarchy.png")
    test("Parent-child column hierarchy with transforms", [
        f'''var scene = new Scene(); scene.setCameraSize(128, 128);
        var p = new Palette(); var ink = p.addColor(0, 0, 0, 255);

        var lv1 = scene.newLevel("Vector", "parent_lv");
        var vi1 = new VectorImage(); vi1.addRect(-30, -30, 30, 30, 2, ink); vi1.setPalette(p);
        lv1.setFrame(1, vi1.toImage());
        scene.setCell(0, 0, lv1, 1);

        var lv2 = scene.newLevel("Vector", "child_lv");
        var vi2 = new VectorImage(); vi2.addCircle(40, 0, 10, 2, ink); vi2.setPalette(p);
        lv2.setFrame(1, vi2.toImage());
        scene.setCell(0, 1, lv2, 1);

        var parentObj = scene.getStageObject(0);
        var childObj = scene.getStageObject(1);
        childObj.setParent(parentObj);
        parentObj.setKeyframe(0, "angle", 30);

        var renderer = new Renderer();
        var img = renderer.renderFrame(scene, 0);
        img.save("{outpath_hier}");
        print("rendered " + img.width + "x" + img.height)''',
    ], lambda r: ("rendered" in output_of(r) and file_exists_and_nonzero(outpath_hier), f"out={output_of(r)}"), group=G)


# ============================================================
#  MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  INTEGRATION TEST SUITE")
    print("  OpenToonz Headless JSON-RPC Interface")
    print("=" * 60)

    # Clean up old test images
    for f in set(glob.glob(os.path.join(TESTDIR, "test*.png"))):
        if os.path.exists(f):
            os.remove(f)

    test_plastic_deformation()
    test_renderer_integration()
    test_multi_column()

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    groups = {}
    for r in results:
        g = r["group"]
        if g not in groups:
            groups[g] = {"pass": 0, "fail": 0}
        if r["passed"]:
            groups[g]["pass"] += 1
        else:
            groups[g]["fail"] += 1

    print(f"\n  Total: {total} tests | PASS: {passed} | FAIL: {failed}\n")

    for g, data in groups.items():
        status = "ALL PASS" if data["fail"] == 0 else f"{data['fail']} FAIL"
        print(f"  {g}: {data['pass']}/{data['pass']+data['fail']} ({status})")

    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for r in failures:
            print(f"    - [{r['group']}] {r['name']}: {r['detail']}")

    # List output files
    output_files = sorted(glob.glob(os.path.join(TESTDIR, "test_*.png")))
    if output_files:
        print(f"\n  OUTPUT FILES:")
        for f in output_files:
            size = os.path.getsize(f)
            print(f"    {os.path.basename(f)}: {size} bytes")

    sys.exit(0 if failed == 0 else 1)
