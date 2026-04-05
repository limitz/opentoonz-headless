

#include "toonz/scriptbinding_plasticrig.h"
#include "ext/plasticskeleton.h"
#include "ext/plasticskeletondeformation.h"
#include "tdoublekeyframe.h"

namespace TScriptBinding {

PlasticRig::PlasticRig()
    : m_skeleton(new PlasticSkeleton())
    , m_deformation(new PlasticSkeletonDeformation()) {
  m_deformation->addRef();
  // Attach skeleton to deformation so that addVertex() automatically
  // creates vertex deformation entries (SkVD) for keyframe animation.
  m_deformation->attach(0, m_skeleton);
  // The default skeleton ID param is 1.0 (for GUI multi-skeleton support).
  // Set it to 0 so the renderer finds our skeleton at ID 0.
  TDoubleKeyframe kf(0, 0.0);
  kf.m_type = TDoubleKeyframe::Constant;
  m_deformation->skeletonIdsParam()->setKeyframe(kf);
}

PlasticRig::~PlasticRig() {
  // Don't delete m_skeleton directly — the deformation holds a smart pointer
  // to it via attach(). Detaching releases the smart pointer's reference.
  if (m_deformation) {
    m_deformation->detach(0);
    m_deformation->release();
  }
}

QScriptValue PlasticRig::toString() {
  return QString("PlasticRig[%1 vertices]").arg(getVertexCount());
}

QScriptValue PlasticRig::ctor(QScriptContext *context,
                              QScriptEngine *engine) {
  return create(engine, new PlasticRig());
}

QScriptValue PlasticRig::addVertex(double x, double y, int parentIdx) {
  PlasticSkeletonVertex vertex(TPointD(x, y));
  int idx = m_skeleton->addVertex(vertex, parentIdx);
  if (idx < 0) {
    return context()->throwError(
        tr("Failed to add vertex (invalid parent index %1)").arg(parentIdx));
  }
  return QScriptValue(idx);
}

QScriptValue PlasticRig::moveVertex(int vertexIdx, double x, double y) {
  if (vertexIdx < 0 || vertexIdx >= getVertexCount()) {
    return context()->throwError(
        tr("Vertex index %1 out of range").arg(vertexIdx));
  }
  m_skeleton->moveVertex(vertexIdx, TPointD(x, y));
  return context()->thisObject();
}

QScriptValue PlasticRig::removeVertex(int vertexIdx) {
  if (vertexIdx < 0 || vertexIdx >= getVertexCount()) {
    return context()->throwError(
        tr("Vertex index %1 out of range").arg(vertexIdx));
  }
  m_skeleton->removeVertex(vertexIdx);
  return context()->thisObject();
}

QScriptValue PlasticRig::setVertexName(int vertexIdx, const QString &name) {
  if (vertexIdx < 0 || vertexIdx >= getVertexCount()) {
    return context()->throwError(
        tr("Vertex index %1 out of range").arg(vertexIdx));
  }
  m_skeleton->setVertexName(vertexIdx, name);
  return context()->thisObject();
}

QScriptValue PlasticRig::setVertexKeyframe(int vertexIdx, double frame,
                                           const QString &param,
                                           double value) {
  if (vertexIdx < 0 || vertexIdx >= getVertexCount()) {
    return context()->throwError(
        tr("Vertex index %1 out of range").arg(vertexIdx));
  }

  // Determine which deformation parameter
  QString p = param.toLower();
  int paramIdx;
  if (p == "angle")
    paramIdx = SkVD::ANGLE;
  else if (p == "distance")
    paramIdx = SkVD::DISTANCE;
  else if (p == "so" || p == "stackingorder")
    paramIdx = SkVD::SO;
  else {
    return context()->throwError(
        tr("Unknown param '%1'. Valid: angle, distance, so").arg(param));
  }

  // Get vertex name to look up deformation
  QString vertexName = m_skeleton->vertex(vertexIdx).name();
  if (vertexName.isEmpty()) {
    // Assign a default name if not set
    vertexName = QString("v%1").arg(vertexIdx);
    m_skeleton->setVertexName(vertexIdx, vertexName);
  }

  SkVD *vd = m_deformation->vertexDeformation(vertexName);
  if (!vd) {
    return context()->throwError(
        tr("Cannot access deformation for vertex %1").arg(vertexIdx));
  }

  TDoubleParam *dp = vd->m_params[paramIdx].getPointer();
  if (!dp) {
    return context()->throwError(tr("Parameter not available"));
  }

  TDoubleKeyframe kf(frame, value);
  kf.m_type = TDoubleKeyframe::Linear;
  dp->setKeyframe(kf);

  return context()->thisObject();
}

int PlasticRig::getVertexCount() const { return m_skeleton->verticesCount(); }

}  // namespace TScriptBinding
