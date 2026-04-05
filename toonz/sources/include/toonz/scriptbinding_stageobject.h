#pragma once

#ifndef SCRIPTBINDING_STAGEOBJECT_H
#define SCRIPTBINDING_STAGEOBJECT_H

#include "toonz/scriptbinding.h"
#include "toonz/tstageobject.h"

namespace TScriptBinding {

class DVAPI StageObject final : public Wrapper {
  Q_OBJECT

  TStageObject *m_obj;           // Not owned — belongs to TXsheet's stage object tree
  TStageObjectTree *m_tree;      // Not owned — for spline access

public:
  StageObject();
  explicit StageObject(TStageObject *obj, TStageObjectTree *tree = nullptr);
  ~StageObject();

  WRAPPER_STD_METHODS(StageObject)
  Q_INVOKABLE QScriptValue toString();

  // Keyframing
  Q_INVOKABLE QScriptValue setKeyframe(double frame, const QString &channel,
                                       double value);
  Q_INVOKABLE QScriptValue getValueAt(double frame, const QString &channel);
  Q_INVOKABLE QScriptValue setInterpolation(double frame,
                                            const QString &channel,
                                            const QString &type);

  // Hierarchy
  Q_INVOKABLE QScriptValue setParent(const QScriptValue &parentObj);
  Q_INVOKABLE QScriptValue setStatus(const QString &status);

  // Motion path
  Q_INVOKABLE QScriptValue setSpline(int splineIdx);

  // Properties
  Q_PROPERTY(QString name READ getName WRITE setName)
  QString getName() const;
  void setName(const QString &name);

  Q_PROPERTY(QString status READ getStatus)
  QString getStatus() const;

  TStageObject *getStageObject() const { return m_obj; }

private:
  TDoubleParam *getChannelParam(const QString &channel);
  static TDoubleKeyframe::Type parseInterpolationType(const QString &type);
};

QScriptValue checkStageObject(QScriptContext *context,
                              const QScriptValue &value, StageObject *&out);

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::StageObject *)

#endif
