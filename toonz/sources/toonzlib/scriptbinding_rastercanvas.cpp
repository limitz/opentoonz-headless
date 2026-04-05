

#include "toonz/scriptbinding_rastercanvas.h"
#include "toonz/scriptbinding_image.h"
#include "toonz/rasterstrokegenerator.h"
#include "toonz/rasterbrush.h"
#include "toonz/fill.h"
#include "ttoonzimage.h"

namespace TScriptBinding {

RasterCanvas::RasterCanvas() : m_width(0), m_height(0) {}

RasterCanvas::RasterCanvas(int width, int height)
    : m_width(width), m_height(height) {
  m_raster = TRasterCM32P(width, height);
  m_raster->clear();
}

RasterCanvas::~RasterCanvas() {}

QScriptValue RasterCanvas::toString() {
  return QString("RasterCanvas[%1x%2]").arg(m_width).arg(m_height);
}

QScriptValue RasterCanvas::ctor(QScriptContext *context,
                                QScriptEngine *engine) {
  QScriptValue err = checkArgumentCount(context, "RasterCanvas", 2);
  if (err.isError()) return err;

  int w = context->argument(0).toInt32();
  int h = context->argument(1).toInt32();
  if (w <= 0 || h <= 0) {
    return context->throwError(
        QObject::tr("Width and height must be positive"));
  }
  return create(engine, new RasterCanvas(w, h));
}

QScriptValue RasterCanvas::brushStroke(const QScriptValue &pointArray,
                                       int styleId, bool antialias) {
  if (!m_raster) {
    return context()->throwError(tr("Canvas not initialized"));
  }
  if (!pointArray.isArray()) {
    return context()->throwError(tr("Expected an array of points"));
  }

  std::vector<TThickPoint> points;
  quint32 len = pointArray.property("length").toUInt32();
  for (quint32 i = 0; i < len; i++) {
    QScriptValue pt = pointArray.property(i);
    if (!pt.isArray()) {
      return context()->throwError(
          tr("Each point must be [x, y] or [x, y, thickness]"));
    }
    double x = pt.property(0).toNumber();
    double y = pt.property(1).toNumber();
    double t = pt.property(2).isUndefined() ? 1.0 : pt.property(2).toNumber();
    points.push_back(TThickPoint(x, y, t));
  }

  if (points.empty()) {
    return context()->throwError(tr("Need at least one point"));
  }

  rasterBrush(m_raster, points, styleId, antialias);
  return context()->thisObject();
}

QScriptValue RasterCanvas::fill(int x, int y, int styleId) {
  if (!m_raster) {
    return context()->throwError(tr("Canvas not initialized"));
  }

  FillParameters params;
  params.m_styleId = styleId;
  params.m_p       = TPoint(x, y);
  params.m_emptyOnly = false;

  ::fill(m_raster, params);
  return context()->thisObject();
}

QScriptValue RasterCanvas::rectFill(int x1, int y1, int x2, int y2,
                                    int styleId) {
  if (!m_raster) {
    return context()->throwError(tr("Canvas not initialized"));
  }

  TRect rect(x1, y1, x2, y2);
  AreaFiller filler(m_raster);
  filler.rectFill(rect, styleId, false, true, true);
  return context()->thisObject();
}

QScriptValue RasterCanvas::inkFill(int x, int y, int styleId, int searchRay) {
  if (!m_raster) {
    return context()->throwError(tr("Canvas not initialized"));
  }

  ::inkFill(m_raster, TPoint(x, y), styleId, searchRay);
  return context()->thisObject();
}

QScriptValue RasterCanvas::clear() {
  if (m_raster) m_raster->clear();
  return context()->thisObject();
}

QScriptValue RasterCanvas::toImage() {
  if (!m_raster) {
    return context()->throwError(tr("Canvas not initialized"));
  }

  TToonzImageP ti(m_raster, m_raster->getBounds());
  TImageP img(ti.getPointer());
  return create(new Image(img));
}

}  // namespace TScriptBinding
