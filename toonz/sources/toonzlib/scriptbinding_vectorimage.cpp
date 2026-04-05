

#include "toonz/scriptbinding_vectorimage.h"
#include "toonz/scriptbinding_stroke.h"
#include "toonz/scriptbinding_image.h"
#include "toonz/scriptbinding_palette.h"
#include <cmath>

namespace TScriptBinding {

VectorImage::VectorImage() : m_vi(new TVectorImage()) {}

VectorImage::VectorImage(const TVectorImageP &vi) : m_vi(vi) {
  if (!m_vi) m_vi = new TVectorImage();
}

VectorImage::~VectorImage() {}

QScriptValue VectorImage::toString() {
  return QString("VectorImage[%1 strokes, %2 regions]")
      .arg(m_vi->getStrokeCount())
      .arg(m_vi->getRegionCount());
}

QScriptValue VectorImage::ctor(QScriptContext *context,
                               QScriptEngine *engine) {
  return create(engine, new VectorImage());
}

QScriptValue VectorImage::addStroke(const QScriptValue &strokeArg) {
  Stroke *s = nullptr;
  QScriptValue err = checkStroke(context(), strokeArg, s);
  if (err.isError()) return err;

  TStroke *stroke = s->getStroke();
  if (!stroke) {
    return context()->throwError(tr("Stroke has no points"));
  }

  // Clone the stroke since TVectorImage takes ownership
  TStroke *clone = new TStroke(*stroke);
  m_vi->addStroke(clone);

  return context()->thisObject();
}

QScriptValue VectorImage::removeStroke(int index) {
  if (index < 0 || index >= (int)m_vi->getStrokeCount()) {
    return context()->throwError(
        tr("Stroke index %1 out of range [0, %2)")
            .arg(index)
            .arg(m_vi->getStrokeCount()));
  }
  m_vi->removeStroke(index);
  return context()->thisObject();
}

QScriptValue VectorImage::getStroke(int index) {
  if (index < 0 || index >= (int)m_vi->getStrokeCount()) {
    return context()->throwError(
        tr("Stroke index %1 out of range [0, %2)")
            .arg(index)
            .arg(m_vi->getStrokeCount()));
  }
  TStroke *s = m_vi->getStroke(index);
  // Wrap without ownership — the VectorImage still owns the stroke
  Stroke *wrapper = new Stroke(s);
  return create(wrapper);
}

QScriptValue VectorImage::findRegions() {
  m_vi->findRegions();
  return context()->thisObject();
}

QScriptValue VectorImage::fill(double x, double y, int styleId) {
  // Ensure regions are computed before filling
  m_vi->findRegions();

  TPointD p(x, y);
  int result = m_vi->fill(p, styleId);
  if (result < 0) {
    return context()->throwError(
        tr("No region found at point (%1, %2)").arg(x).arg(y));
  }
  return context()->thisObject();
}

QScriptValue VectorImage::setEdgeColors(int strokeIndex, int leftColorIdx,
                                        int rightColorIdx) {
  if (strokeIndex < 0 || strokeIndex >= (int)m_vi->getStrokeCount()) {
    return context()->throwError(
        tr("Stroke index %1 out of range").arg(strokeIndex));
  }
  m_vi->setEdgeColors(strokeIndex, leftColorIdx, rightColorIdx);
  return context()->thisObject();
}

QScriptValue VectorImage::group(int fromIndex, int count) {
  if (fromIndex < 0 || fromIndex + count > (int)m_vi->getStrokeCount()) {
    return context()->throwError(tr("Invalid group range"));
  }
  m_vi->group(fromIndex, count);
  return context()->thisObject();
}

QScriptValue VectorImage::ungroup(int index) {
  if (index < 0 || index >= (int)m_vi->getStrokeCount()) {
    return context()->throwError(tr("Stroke index out of range"));
  }
  m_vi->ungroup(index);
  return context()->thisObject();
}

QScriptValue VectorImage::merge(const QScriptValue &otherArg) {
  VectorImage *other = nullptr;
  QScriptValue err   = checkVectorImage(context(), otherArg, other);
  if (err.isError()) return err;

  TAffine identity;
  m_vi->mergeImage(other->getVectorImage(), identity);
  return context()->thisObject();
}

// Helper: add a single built stroke to this VectorImage
static void addBuiltStroke(TVectorImageP &vi, const std::vector<TThickPoint> &pts,
                           int styleId) {
  TStroke *s = new TStroke(pts);
  s->setStyle(styleId);
  vi->addStroke(s);
}

QScriptValue VectorImage::addLine(double x1, double y1, double x2, double y2,
                                  double thickness, int styleId) {
  std::vector<TThickPoint> pts = {TThickPoint(x1, y1, thickness),
                                  TThickPoint(x2, y2, thickness)};
  addBuiltStroke(m_vi, pts, styleId);
  return context()->thisObject();
}

QScriptValue VectorImage::addRect(double x1, double y1, double x2, double y2,
                                  double thickness, int styleId) {
  // 4 edge strokes forming a fillable rectangle
  std::vector<TThickPoint> top = {TThickPoint(x1, y1, thickness),
                                  TThickPoint(x2, y1, thickness)};
  std::vector<TThickPoint> right = {TThickPoint(x2, y1, thickness),
                                    TThickPoint(x2, y2, thickness)};
  std::vector<TThickPoint> bottom = {TThickPoint(x2, y2, thickness),
                                     TThickPoint(x1, y2, thickness)};
  std::vector<TThickPoint> left = {TThickPoint(x1, y2, thickness),
                                   TThickPoint(x1, y1, thickness)};
  addBuiltStroke(m_vi, top, styleId);
  addBuiltStroke(m_vi, right, styleId);
  addBuiltStroke(m_vi, bottom, styleId);
  addBuiltStroke(m_vi, left, styleId);
  return context()->thisObject();
}

QScriptValue VectorImage::addCircle(double cx, double cy, double radius,
                                    double thickness, int styleId,
                                    int segments) {
  if (segments < 3) segments = 3;
  // Generate arc strokes between adjacent points
  double step = 2.0 * M_PI / segments;
  for (int i = 0; i < segments; i++) {
    double a0 = i * step;
    double a1 = (i + 1) * step;
    double amid = (a0 + a1) / 2.0;
    // Use 3 points per segment for smooth Bezier arcs
    std::vector<TThickPoint> pts = {
        TThickPoint(cx + radius * cos(a0), cy + radius * sin(a0), thickness),
        TThickPoint(cx + radius * cos(amid), cy + radius * sin(amid), thickness),
        TThickPoint(cx + radius * cos(a1), cy + radius * sin(a1), thickness)};
    addBuiltStroke(m_vi, pts, styleId);
  }
  return context()->thisObject();
}

QScriptValue VectorImage::addEllipse(double cx, double cy, double rx,
                                     double ry, double thickness, int styleId,
                                     int segments) {
  if (segments < 3) segments = 3;
  double step = 2.0 * M_PI / segments;
  for (int i = 0; i < segments; i++) {
    double a0 = i * step;
    double a1 = (i + 1) * step;
    double amid = (a0 + a1) / 2.0;
    std::vector<TThickPoint> pts = {
        TThickPoint(cx + rx * cos(a0), cy + ry * sin(a0), thickness),
        TThickPoint(cx + rx * cos(amid), cy + ry * sin(amid), thickness),
        TThickPoint(cx + rx * cos(a1), cy + ry * sin(a1), thickness)};
    addBuiltStroke(m_vi, pts, styleId);
  }
  return context()->thisObject();
}

QScriptValue VectorImage::addPolygon(double cx, double cy, double radius,
                                     int sides, double thickness, int styleId) {
  if (sides < 3) sides = 3;
  // Each side is a straight edge (2-point stroke)
  double step = 2.0 * M_PI / sides;
  for (int i = 0; i < sides; i++) {
    double a0 = i * step - M_PI / 2;  // Start at top
    double a1 = (i + 1) * step - M_PI / 2;
    std::vector<TThickPoint> pts = {
        TThickPoint(cx + radius * cos(a0), cy + radius * sin(a0), thickness),
        TThickPoint(cx + radius * cos(a1), cy + radius * sin(a1), thickness)};
    addBuiltStroke(m_vi, pts, styleId);
  }
  return context()->thisObject();
}

QScriptValue VectorImage::addFilledRect(double x1, double y1, double x2,
                                        double y2, double thickness,
                                        int inkStyleId, int fillStyleId) {
  addRect(x1, y1, x2, y2, thickness, inkStyleId);
  m_vi->findRegions();
  double cx = (x1 + x2) * 0.5, cy = (y1 + y2) * 0.5;
  m_vi->fill(TPointD(cx, cy), fillStyleId);
  return context()->thisObject();
}

QScriptValue VectorImage::addFilledCircle(double cx, double cy, double radius,
                                          double thickness, int inkStyleId,
                                          int fillStyleId, int segments) {
  addCircle(cx, cy, radius, thickness, inkStyleId, segments);
  m_vi->findRegions();
  m_vi->fill(TPointD(cx, cy), fillStyleId);
  return context()->thisObject();
}

QScriptValue VectorImage::addFilledPolygon(double cx, double cy, double radius,
                                           int sides, double thickness,
                                           int inkStyleId, int fillStyleId) {
  addPolygon(cx, cy, radius, sides, thickness, inkStyleId);
  m_vi->findRegions();
  m_vi->fill(TPointD(cx, cy), fillStyleId);
  return context()->thisObject();
}

QScriptValue VectorImage::addFilledEllipse(double cx, double cy, double rx,
                                           double ry, double thickness,
                                           int inkStyleId, int fillStyleId,
                                           int segments) {
  addEllipse(cx, cy, rx, ry, thickness, inkStyleId, segments);
  m_vi->findRegions();
  m_vi->fill(TPointD(cx, cy), fillStyleId);
  return context()->thisObject();
}

QScriptValue VectorImage::setPalette(const QScriptValue &paletteArg) {
  Palette *pal = nullptr;
  QScriptValue err = checkPalette(context(), paletteArg, pal);
  if (err.isError()) return err;
  m_vi->setPalette(pal->getPalette());
  return context()->thisObject();
}

QScriptValue VectorImage::toImage() {
  if (!m_vi->getPalette()) {
    return context()->throwError(
        tr("VectorImage has no palette set. Call setPalette() first."));
  }
  TImageP img(m_vi.getPointer());
  return create(new Image(img));
}

int VectorImage::getStrokeCount() const { return m_vi->getStrokeCount(); }

int VectorImage::getRegionCount() const { return m_vi->getRegionCount(); }

QScriptValue checkVectorImage(QScriptContext *context,
                              const QScriptValue &value,
                              VectorImage *&out) {
  out = qscriptvalue_cast<VectorImage *>(value);
  if (!out)
    return context->throwError(QObject::tr("Expected a VectorImage object"));
  return QScriptValue();
}

}  // namespace TScriptBinding
