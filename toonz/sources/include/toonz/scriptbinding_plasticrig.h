#pragma once

#ifndef SCRIPTBINDING_PLASTICRIG_H
#define SCRIPTBINDING_PLASTICRIG_H

#include "toonz/scriptbinding.h"

// Forward declarations — avoid heavy includes in header
class PlasticSkeleton;
class PlasticSkeletonDeformation;

namespace TScriptBinding {

class DVAPI PlasticRig final : public Wrapper {
  Q_OBJECT

  PlasticSkeleton *m_skeleton;
  PlasticSkeletonDeformation *m_deformation;

public:
  PlasticRig();
  ~PlasticRig();

  WRAPPER_STD_METHODS(PlasticRig)
  Q_INVOKABLE QScriptValue toString();

  // Vertex operations
  Q_INVOKABLE QScriptValue addVertex(double x, double y, int parentIdx = -1);
  Q_INVOKABLE QScriptValue moveVertex(int vertexIdx, double x, double y);
  Q_INVOKABLE QScriptValue removeVertex(int vertexIdx);
  Q_INVOKABLE QScriptValue setVertexName(int vertexIdx, const QString &name);

  // Keyframing deformation
  Q_INVOKABLE QScriptValue setVertexKeyframe(int vertexIdx, double frame,
                                             const QString &param,
                                             double value);

  // Properties
  Q_PROPERTY(int vertexCount READ getVertexCount)
  int getVertexCount() const;

  PlasticSkeleton *getSkeleton() const { return m_skeleton; }
  PlasticSkeletonDeformation *getDeformation() const { return m_deformation; }
};

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::PlasticRig *)

#endif
