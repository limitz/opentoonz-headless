

#include "toonz/scriptbinding_tracker.h"
#include "toonz/scriptbinding_image.h"
#include "toonz/scriptbinding_level.h"
#include "tracker_objecttracker.h"
#include "trasterimage.h"
#include "ttoonzimage.h"
#include "tpalette.h"
#include "tcolorstyles.h"
#include "trop.h"

#include <vector>

namespace TScriptBinding {

// ---------------------------------------------------------------
//  Internal region definition
// ---------------------------------------------------------------

struct TrackRegion {
  int x, y, width, height;
};

// ---------------------------------------------------------------
//  Tracker::Imp
// ---------------------------------------------------------------

class Tracker::Imp {
public:
  double m_threshold;
  double m_sensitivity;
  bool m_variableRegion;
  bool m_includeBackground;
  std::vector<TrackRegion> m_regions;

  Imp()
      : m_threshold(0.2),
        m_sensitivity(0.01),
        m_variableRegion(false),
        m_includeBackground(false) {}
};

// ---------------------------------------------------------------
//  Tracker
// ---------------------------------------------------------------

Tracker::Tracker() : m_imp(new Imp()) {}
Tracker::~Tracker() { delete m_imp; }

QScriptValue Tracker::toString() { return "Tracker"; }

QScriptValue Tracker::ctor(QScriptContext *context, QScriptEngine *engine) {
  return create(engine, new Tracker());
}

QScriptValue Tracker::addRegion(int x, int y, int width, int height) {
  if (width <= 0 || height <= 0)
    return context()->throwError(tr("Region width and height must be > 0"));

  TrackRegion r;
  r.x      = x;
  r.y      = y;
  r.width  = width;
  r.height = height;
  m_imp->m_regions.push_back(r);
  return QScriptValue((int)m_imp->m_regions.size() - 1);
}

// Helper: convert an Image to TRaster32P
static TRaster32P imageToRaster32(const TImageP &img) {
  if (TRasterImageP ri = img) {
    TRasterP ras = ri->getRaster();
    if (TRaster32P r32 = ras) return r32;
    // Convert other raster types
    TRaster32P r32(ras->getSize());
    TRop::convert(r32, ras);
    return r32;
  }
  if (TToonzImageP ti = img) {
    TRasterCM32P cmRas = ti->getRaster();
    TRaster32P r32(cmRas->getSize());
    r32->clear();
    TPalette *pal = ti->getPalette();
    if (pal) {
      for (int y = 0; y < cmRas->getLy(); y++) {
        TPixelCM32 *cmPix = cmRas->pixels(y);
        TPixel32 *px      = r32->pixels(y);
        for (int x = 0; x < cmRas->getLx(); x++) {
          int inkId    = cmPix[x].getInk();
          int paintId  = cmPix[x].getPaint();
          int tone     = cmPix[x].getTone();
          TColorStyle *inkStyle   = pal->getStyle(inkId);
          TColorStyle *paintStyle = pal->getStyle(paintId);
          TPixel32 inkColor =
              inkStyle ? inkStyle->getAverageColor() : TPixel32::Black;
          TPixel32 paintColor =
              paintStyle ? paintStyle->getAverageColor() : TPixel32::White;
          // Blend ink and paint based on tone (0=ink, 255=paint)
          int t  = tone;
          px[x].r = (inkColor.r * (255 - t) + paintColor.r * t) / 255;
          px[x].g = (inkColor.g * (255 - t) + paintColor.g * t) / 255;
          px[x].b = (inkColor.b * (255 - t) + paintColor.b * t) / 255;
          px[x].m = 255;
        }
      }
    }
    return r32;
  }
  return TRaster32P();
}

QScriptValue Tracker::track(QScriptValue levelArg, int fromFrame, int toFrame) {
  Level *level = qscriptvalue_cast<Level *>(levelArg);
  if (!level)
    return context()->throwError(tr("First argument must be a Level"));

  if (m_imp->m_regions.empty())
    return context()->throwError(tr("No tracking regions defined. Call addRegion() first"));

  if (fromFrame < 1 || toFrame < fromFrame)
    return context()->throwError(
        tr("Invalid frame range: from=%1 to=%2").arg(fromFrame).arg(toFrame));

  // Collect frame images
  QList<TFrameId> fids;
  level->getFrameIds(fids);

  // Build ordered list of frames in range
  std::vector<std::pair<TFrameId, TRaster32P>> frames;
  for (const TFrameId &fid : fids) {
    int fn = fid.getNumber();
    if (fn < fromFrame || fn > toFrame) continue;
    TImageP img = level->getImg(fid);
    TRaster32P r32 = imageToRaster32(img);
    if (!r32) continue;
    frames.push_back({fid, r32});
  }

  if (frames.empty())
    return context()->throwError(tr("No frames found in range [%1, %2]")
                                     .arg(fromFrame)
                                     .arg(toFrame));

  int imW = frames[0].second->getLx();
  int imH = frames[0].second->getLy();

  int regionCount = (int)m_imp->m_regions.size();

  // Create per-region trackers
  std::vector<std::unique_ptr<CObjectTracker>> trackers;
  for (int i = 0; i < regionCount; i++) {
    auto tracker = std::make_unique<CObjectTracker>(
        imW, imH, true, m_imp->m_includeBackground, false);

    const TrackRegion &r = m_imp->m_regions[i];
    // CObjectTracker uses Y-flipped coords (0 at top)
    int cy = imH - 1 - r.y;  // flip Y
    short dimTemp = std::max(r.width, r.height) / 2;
    if (dimTemp < 5) dimTemp = 5;

    tracker->ObjectTrackerInitObjectParameters(
        (short)i,
        (short)r.x, (short)cy,
        (short)r.width, (short)r.height,
        dimTemp,                                       // search template area
        m_imp->m_variableRegion ? (short)3 : (short)0, // variation window
        (float)m_imp->m_threshold,                     // lose threshold
        (float)(m_imp->m_threshold * 0.5)              // warning threshold
    );
    trackers.push_back(std::move(tracker));
  }

  // Initialize trackers on first frame
  TRaster32P firstRas = frames[0].second;
  for (auto &t : trackers) {
    t->ObjeckTrackerHandlerByUser(&firstRas);
  }

  // Prepare result storage
  // results[regionIdx] = {xs, ys, statuses}
  struct RegionResult {
    std::vector<double> xs, ys;
    std::vector<std::string> statuses;
  };
  std::vector<RegionResult> results(regionCount);

  // Store initial positions
  for (int i = 0; i < regionCount; i++) {
    NEIGHBOUR pos = trackers[i]->GetPosition();
    results[i].xs.push_back(pos.X);
    results[i].ys.push_back(imH - 1 - pos.Y);  // flip back
    results[i].statuses.push_back("VISIBLE");
  }

  // Track through subsequent frames
  for (size_t fi = 1; fi < frames.size(); fi++) {
    TRaster32P ras = frames[fi].second;

    // Create template from previous frame for matching
    TRaster32P prevRas = frames[fi - 1].second;

    for (int i = 0; i < regionCount; i++) {
      // Mean-shift tracking
      trackers[i]->FindNextLocation(&ras);

      // Template matching
      float dist = trackers[i]->Matching(&ras, &prevRas);

      // Update template if good match
      if (dist < m_imp->m_sensitivity) {
        trackers[i]->updateTemp();
      }

      NEIGHBOUR pos = trackers[i]->GetPosition();
      std::string vis = trackers[i]->GetVisibility();
      if (vis.empty()) vis = "VISIBLE";

      results[i].xs.push_back((double)pos.X);
      results[i].ys.push_back((double)(imH - 1 - pos.Y));  // flip back
      results[i].statuses.push_back(vis);
    }
  }

  // Build JS result array
  QScriptValue arr = engine()->newArray(regionCount);
  for (int i = 0; i < regionCount; i++) {
    QScriptValue regionObj = engine()->newObject();

    QScriptValue xArr = engine()->newArray((int)results[i].xs.size());
    QScriptValue yArr = engine()->newArray((int)results[i].ys.size());
    QScriptValue sArr = engine()->newArray((int)results[i].statuses.size());

    for (int f = 0; f < (int)results[i].xs.size(); f++) {
      xArr.setProperty(f, results[i].xs[f]);
      yArr.setProperty(f, results[i].ys[f]);
      sArr.setProperty(f, QString::fromStdString(results[i].statuses[f]));
    }

    regionObj.setProperty("x", xArr);
    regionObj.setProperty("y", yArr);
    regionObj.setProperty("status", sArr);

    arr.setProperty(i, regionObj);
  }

  return arr;
}

// ---------------------------------------------------------------
//  Properties
// ---------------------------------------------------------------

double Tracker::getThreshold() const { return m_imp->m_threshold; }
void Tracker::setThreshold(double v) {
  m_imp->m_threshold = std::max(0.0, std::min(1.0, v));
}

double Tracker::getSensitivity() const { return m_imp->m_sensitivity; }
void Tracker::setSensitivity(double v) {
  m_imp->m_sensitivity = std::max(0.0, std::min(1.0, v));
}

bool Tracker::getVariableRegion() const { return m_imp->m_variableRegion; }
void Tracker::setVariableRegion(bool v) { m_imp->m_variableRegion = v; }

bool Tracker::getIncludeBackground() const {
  return m_imp->m_includeBackground;
}
void Tracker::setIncludeBackground(bool v) { m_imp->m_includeBackground = v; }

}  // namespace TScriptBinding
