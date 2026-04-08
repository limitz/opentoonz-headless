

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
  if (thickness < 0) thickness = 0;
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
    if (t < 0) t = 0;
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

QScriptValue Stroke::getPoint(int index) {
  if (m_stroke) {
    int n = m_stroke->getControlPointCount();
    if (index < 0 || index >= n)
      return context()->throwError(
          tr("Point index %1 out of range [0, %2)").arg(index).arg(n));
    TThickPoint p = m_stroke->getControlPoint(index);
    QScriptValue arr = engine()->newArray(3);
    arr.setProperty(0, p.x);
    arr.setProperty(1, p.y);
    arr.setProperty(2, p.thick);
    return arr;
  } else {
    if (index < 0 || index >= (int)m_points.size())
      return context()->throwError(
          tr("Point index %1 out of range [0, %2)")
              .arg(index)
              .arg(m_points.size()));
    TThickPoint p = m_points[index];
    QScriptValue arr = engine()->newArray(3);
    arr.setProperty(0, p.x);
    arr.setProperty(1, p.y);
    arr.setProperty(2, p.thick);
    return arr;
  }
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

QScriptValue Stroke::setCapStyle(const QString &style) {
  QString s = style.toLower();
  if (s == "butt")
    m_outlineOptions.m_capStyle = TStroke::OutlineOptions::BUTT_CAP;
  else if (s == "round")
    m_outlineOptions.m_capStyle = TStroke::OutlineOptions::ROUND_CAP;
  else if (s == "projecting")
    m_outlineOptions.m_capStyle = TStroke::OutlineOptions::PROJECTING_CAP;
  else
    return context()->throwError(
        tr("Unknown cap style '%1'. Valid: butt, round, projecting")
            .arg(style));
  if (m_stroke) m_stroke->outlineOptions() = m_outlineOptions;
  return context()->thisObject();
}

QScriptValue Stroke::setJoinStyle(const QString &style) {
  QString s = style.toLower();
  if (s == "miter")
    m_outlineOptions.m_joinStyle = TStroke::OutlineOptions::MITER_JOIN;
  else if (s == "round")
    m_outlineOptions.m_joinStyle = TStroke::OutlineOptions::ROUND_JOIN;
  else if (s == "bevel")
    m_outlineOptions.m_joinStyle = TStroke::OutlineOptions::BEVEL_JOIN;
  else
    return context()->throwError(
        tr("Unknown join style '%1'. Valid: miter, round, bevel")
            .arg(style));
  if (m_stroke) m_stroke->outlineOptions() = m_outlineOptions;
  return context()->thisObject();
}

QScriptValue Stroke::setMiterLimit(double limit) {
  if (limit < 0)
    return context()->throwError(tr("Miter limit must be >= 0"));
  m_outlineOptions.m_miterUpper = limit;
  if (m_stroke) m_stroke->outlineOptions() = m_outlineOptions;
  return context()->thisObject();
}

void Stroke::ensureBuilt() {
  if (m_stroke) return;
  if (m_points.empty()) return;
  m_stroke = new TStroke(m_points);
  m_stroke->addRef();
  m_stroke->setStyle(m_styleId);
  m_stroke->outlineOptions() = m_outlineOptions;
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
