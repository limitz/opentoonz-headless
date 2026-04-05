

#include "toonz/scriptbinding_stroke.h"

namespace TScriptBinding {

Stroke::Stroke() : m_stroke(nullptr), m_styleId(1) {}

Stroke::Stroke(TStroke *stroke) : m_stroke(stroke), m_styleId(1) {
  if (m_stroke) {
    m_stroke->addRef();
    m_styleId = m_stroke->getStyle();
  }
}

Stroke::~Stroke() {
  if (m_stroke) m_stroke->release();
}

QScriptValue Stroke::toString() {
  int n = m_stroke ? m_stroke->getControlPointCount() : (int)m_points.size();
  return QString("Stroke[%1 points]").arg(n);
}

QScriptValue Stroke::ctor(QScriptContext *context, QScriptEngine *engine) {
  return create(engine, new Stroke());
}

QScriptValue Stroke::addPoint(double x, double y, double thickness) {
  if (m_stroke) {
    return context()->throwError(
        tr("Cannot add points to an already built stroke"));
  }
  m_points.push_back(TThickPoint(x, y, thickness));
  return context()->thisObject();
}

QScriptValue Stroke::addPoints(const QScriptValue &pointArray) {
  if (m_stroke) {
    return context()->throwError(
        tr("Cannot add points to an already built stroke"));
  }
  if (!pointArray.isArray()) {
    return context()->throwError(tr("Expected an array of points"));
  }
  quint32 len = pointArray.property("length").toUInt32();
  for (quint32 i = 0; i < len; i++) {
    QScriptValue pt = pointArray.property(i);
    if (!pt.isArray()) {
      return context()->throwError(
          tr("Each point must be an array [x, y, thickness]"));
    }
    double x = pt.property(0).toNumber();
    double y = pt.property(1).toNumber();
    double t = pt.property(2).isUndefined() ? 1.0 : pt.property(2).toNumber();
    m_points.push_back(TThickPoint(x, y, t));
  }
  return context()->thisObject();
}

QScriptValue Stroke::build() {
  ensureBuilt();
  if (!m_stroke) {
    return context()->throwError(tr("Need at least 1 point to build a stroke"));
  }
  return context()->thisObject();
}

QScriptValue Stroke::close() {
  ensureBuilt();
  if (m_stroke) {
    m_stroke->setSelfLoop(true);
  }
  return context()->thisObject();
}

QScriptValue Stroke::setStyle(int styleId) {
  m_styleId = styleId;
  if (m_stroke) m_stroke->setStyle(styleId);
  return context()->thisObject();
}

double Stroke::getLength() const {
  return m_stroke ? m_stroke->getLength() : 0.0;
}

int Stroke::getPointCount() const {
  return m_stroke ? m_stroke->getControlPointCount() : (int)m_points.size();
}

int Stroke::getStyle() const { return m_styleId; }

void Stroke::setStyleProp(int v) {
  m_styleId = v;
  if (m_stroke) m_stroke->setStyle(v);
}

TStroke *Stroke::getStroke() {
  ensureBuilt();
  return m_stroke;
}

void Stroke::ensureBuilt() {
  if (m_stroke) return;
  if (m_points.empty()) return;
  m_stroke = new TStroke(m_points);
  m_stroke->addRef();
  m_stroke->setStyle(m_styleId);
  m_points.clear();
}

QScriptValue checkStroke(QScriptContext *context, const QScriptValue &value,
                         Stroke *&out) {
  out = qscriptvalue_cast<Stroke *>(value);
  if (!out)
    return context->throwError(QObject::tr("Expected a Stroke object"));
  return QScriptValue();
}

}  // namespace TScriptBinding
