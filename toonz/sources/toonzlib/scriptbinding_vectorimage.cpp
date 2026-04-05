

#include "toonz/scriptbinding_vectorimage.h"
#include "toonz/scriptbinding_stroke.h"
#include "toonz/scriptbinding_image.h"
#include "toonz/scriptbinding_palette.h"

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
