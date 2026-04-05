

#include "toonz/scriptbinding_stageobject.h"
#include "toonz/scriptbinding_plasticrig.h"
#include "toonz/tstageobjectspline.h"
#include "toonz/tstageobjecttree.h"
#include "toonz/ikengine.h"
#include "ext/plasticskeletondeformation.h"
#include "tdoublekeyframe.h"

namespace TScriptBinding {

StageObject::StageObject() : m_obj(nullptr), m_tree(nullptr) {}

StageObject::StageObject(TStageObject *obj, TStageObjectTree *tree)
    : m_obj(obj), m_tree(tree) {}

StageObject::~StageObject() {}

QScriptValue StageObject::toString() {
  if (!m_obj) return "StageObject[null]";
  return QString("StageObject[%1]").arg(getName());
}

QScriptValue StageObject::ctor(QScriptContext *context,
                               QScriptEngine *engine) {
  return context->throwError(
      QObject::tr("StageObject cannot be created directly; use "
                  "scene.getStageObject(colIdx)"));
}

TDoubleParam *StageObject::getChannelParam(const QString &channel) {
  if (!m_obj) return nullptr;
  QString ch = channel.toLower();
  if (ch == "x") return m_obj->getParam(TStageObject::T_X);
  if (ch == "y") return m_obj->getParam(TStageObject::T_Y);
  if (ch == "z") return m_obj->getParam(TStageObject::T_Z);
  if (ch == "angle" || ch == "rotation")
    return m_obj->getParam(TStageObject::T_Angle);
  if (ch == "so" || ch == "stackingorder")
    return m_obj->getParam(TStageObject::T_SO);
  if (ch == "scalex") return m_obj->getParam(TStageObject::T_ScaleX);
  if (ch == "scaley") return m_obj->getParam(TStageObject::T_ScaleY);
  if (ch == "scale") return m_obj->getParam(TStageObject::T_Scale);
  if (ch == "shearx") return m_obj->getParam(TStageObject::T_ShearX);
  if (ch == "sheary") return m_obj->getParam(TStageObject::T_ShearY);
  if (ch == "path") return m_obj->getParam(TStageObject::T_Path);
  return nullptr;
}

TDoubleKeyframe::Type StageObject::parseInterpolationType(
    const QString &type) {
  QString t = type.toLower();
  if (t == "constant" || t == "hold") return TDoubleKeyframe::Constant;
  if (t == "linear") return TDoubleKeyframe::Linear;
  if (t == "speedinout" || t == "bezier") return TDoubleKeyframe::SpeedInOut;
  if (t == "easeinout" || t == "ease") return TDoubleKeyframe::EaseInOut;
  if (t == "easeinoutpercentage")
    return TDoubleKeyframe::EaseInOutPercentage;
  if (t == "exponential") return TDoubleKeyframe::Exponential;
  return TDoubleKeyframe::None;
}

QScriptValue StageObject::setKeyframe(double frame, const QString &channel,
                                      double value) {
  if (!m_obj) return context()->throwError(tr("StageObject is null"));
  if (frame < 0)
    return context()->throwError(tr("Frame must be >= 0, got %1").arg(frame));

  TDoubleParam *param = getChannelParam(channel);
  if (!param) {
    return context()->throwError(
        tr("Unknown channel '%1'. Valid: x, y, z, angle, scalex, scaley, "
           "scale, shearx, sheary, so, path")
            .arg(channel));
  }

  TDoubleKeyframe kf(frame, value);
  kf.m_type = TDoubleKeyframe::Linear;  // Default to linear
  param->setKeyframe(kf);

  return context()->thisObject();
}

QScriptValue StageObject::getValueAt(double frame, const QString &channel) {
  if (!m_obj) return context()->throwError(tr("StageObject is null"));

  TDoubleParam *param = getChannelParam(channel);
  if (!param) {
    return context()->throwError(tr("Unknown channel '%1'").arg(channel));
  }

  return QScriptValue(param->getValue(frame));
}

QScriptValue StageObject::setInterpolation(double frame,
                                           const QString &channel,
                                           const QString &type) {
  if (!m_obj) return context()->throwError(tr("StageObject is null"));

  TDoubleParam *param = getChannelParam(channel);
  if (!param) {
    return context()->throwError(tr("Unknown channel '%1'").arg(channel));
  }

  TDoubleKeyframe::Type interpType = parseInterpolationType(type);
  if (interpType == TDoubleKeyframe::None) {
    return context()->throwError(
        tr("Unknown interpolation type '%1'. Valid: constant, linear, "
           "speedInOut, easeInOut, exponential")
            .arg(type));
  }

  // Find the keyframe at this frame and update its type
  for (int i = 0; i < param->getKeyframeCount(); i++) {
    TDoubleKeyframe kf = param->getKeyframe(i);
    if (kf.m_frame == frame) {
      kf.m_type = interpType;
      param->setKeyframe(kf);
      return context()->thisObject();
    }
  }

  return context()->throwError(
      tr("No keyframe found at frame %1 on channel '%2'")
          .arg(frame)
          .arg(channel));
}

QScriptValue StageObject::setPlasticRig(const QScriptValue &rigArg) {
  if (!m_obj) return context()->throwError(tr("StageObject is null"));

  PlasticRig *rig = qscriptvalue_cast<PlasticRig *>(rigArg);
  if (!rig) {
    return context()->throwError(tr("Expected a PlasticRig argument"));
  }

  PlasticSkeletonDeformation *def = rig->getDeformation();
  if (!def) {
    return context()->throwError(tr("PlasticRig has no deformation data"));
  }

  PlasticSkeletonDeformationP sdp(def);
  m_obj->setPlasticSkeletonDeformation(sdp);
  return context()->thisObject();
}

QScriptValue StageObject::setSpline(int splineIdx) {
  if (!m_obj) return context()->throwError(tr("StageObject is null"));

  TStageObjectTree *tree = m_tree;
  if (!tree) {
    return context()->throwError(tr("StageObject has no tree reference"));
  }

  if (splineIdx < 0 || splineIdx >= tree->getSplineCount()) {
    return context()->throwError(
        tr("Spline index %1 out of range [0, %2)")
            .arg(splineIdx)
            .arg(tree->getSplineCount()));
  }

  TStageObjectSpline *spline = tree->getSpline(splineIdx);
  m_obj->setSpline(spline);
  return context()->thisObject();
}

QScriptValue StageObject::solveIK(double targetX, double targetY,
                                  double frame) {
  if (!m_obj) return context()->throwError(tr("StageObject is null"));
  if (!m_tree) return context()->throwError(tr("StageObject has no tree reference"));
  if (frame < 0)
    return context()->throwError(tr("Frame must be >= 0"));

  // Walk the parent chain from this object up to root, collecting the chain
  std::vector<TStageObject *> chain;
  TStageObject *cur = m_obj;
  while (cur) {
    chain.push_back(cur);
    TStageObjectId parentId = cur->getParent();
    if (!parentId.isColumn() && !parentId.isTable()) break;
    TStageObject *parent = m_tree->getStageObject(parentId, false);
    if (!parent || parent == cur) break;
    cur = parent;
  }

  if (chain.size() < 2) {
    return context()->throwError(
        tr("IK needs at least 2 objects in parent chain"));
  }

  // Reverse so chain goes root -> ... -> this object
  std::reverse(chain.begin(), chain.end());

  // Build IK engine from chain positions at current frame
  IKEngine ik;
  TPointD rootPos = chain[0]->getCenter(frame);
  ik.setRoot(rootPos);

  // Store initial angles for computing deltas later
  std::vector<double> initialAngles;
  initialAngles.push_back(
      chain[0]->getParam(TStageObject::T_Angle)->getValue(frame));

  for (int i = 1; i < (int)chain.size(); i++) {
    TPointD pos = chain[i]->getCenter(frame);
    ik.addJoint(pos, i - 1);
    initialAngles.push_back(
        chain[i]->getParam(TStageObject::T_Angle)->getValue(frame));
  }

  // Solve: drag the last joint to the target
  TPointD target(targetX, targetY);
  ik.drag(target);

  // Extract solved angles and apply as keyframes
  // IKEngine returns absolute geometric angles; we compute deltas
  // relative to initial angles and apply them
  QScriptValue result = engine()->newArray();
  for (int i = 0; i < (int)chain.size() - 1; i++) {
    double solvedAngle = ik.getJointAngle(i) * (180.0 / M_PI);
    double delta       = solvedAngle - initialAngles[i];
    double newAngle    = initialAngles[i + 1] + delta;

    TDoubleParam *param =
        chain[i + 1]->getParam(TStageObject::T_Angle);
    TDoubleKeyframe kf(frame, newAngle);
    kf.m_type = TDoubleKeyframe::Linear;
    param->setKeyframe(kf);

    result.setProperty(i, newAngle);
  }

  return result;
}

QScriptValue StageObject::setParent(const QScriptValue &parentArg) {
  if (!m_obj) return context()->throwError(tr("StageObject is null"));

  StageObject *parent = nullptr;
  QScriptValue err    = checkStageObject(context(), parentArg, parent);
  if (err.isError()) return err;

  if (!parent->getStageObject()) {
    return context()->throwError(tr("Parent StageObject is null"));
  }

  m_obj->setParent(parent->getStageObject()->getId());
  return context()->thisObject();
}

QScriptValue StageObject::setStatus(const QString &status) {
  if (!m_obj) return context()->throwError(tr("StageObject is null"));

  QString s = status.toLower();
  if (s == "xy")
    m_obj->setStatus(TStageObject::XY);
  else if (s == "path")
    m_obj->setStatus(TStageObject::PATH);
  else if (s == "pathaim")
    m_obj->setStatus(TStageObject::PATH_AIM);
  else if (s == "ik")
    m_obj->setStatus(TStageObject::IK);
  else
    return context()->throwError(
        tr("Unknown status '%1'. Valid: xy, path, pathAim, ik").arg(status));

  return context()->thisObject();
}

QString StageObject::getName() const {
  if (!m_obj) return "";
  return QString::fromStdString(m_obj->getName());
}

void StageObject::setName(const QString &name) {
  if (m_obj) m_obj->setName(name.toStdString());
}

QString StageObject::getStatus() const {
  if (!m_obj) return "";
  switch (m_obj->getStatus()) {
  case TStageObject::XY: return "xy";
  case TStageObject::PATH: return "path";
  case TStageObject::PATH_AIM: return "pathAim";
  case TStageObject::IK: return "ik";
  default: return "unknown";
  }
}

QScriptValue checkStageObject(QScriptContext *context,
                              const QScriptValue &value, StageObject *&out) {
  out = qscriptvalue_cast<StageObject *>(value);
  if (!out)
    return context->throwError(QObject::tr("Expected a StageObject"));
  return QScriptValue();
}

}  // namespace TScriptBinding
