#pragma once

#ifndef SCRIPTBINDING_EFFECT_H
#define SCRIPTBINDING_EFFECT_H

#include "toonz/scriptbinding.h"
#include "tfx.h"

namespace TScriptBinding {

class DVAPI Effect final : public Wrapper {
  Q_OBJECT

  TFxP m_fx;

public:
  Effect();
  explicit Effect(const TFxP &fx);
  ~Effect();

  WRAPPER_STD_METHODS(Effect)
  Q_INVOKABLE QScriptValue toString();

  // Parameter access
  Q_INVOKABLE QScriptValue setParam(const QString &name,
                                    const QScriptValue &value);
  Q_INVOKABLE QScriptValue getParam(const QString &name);
  Q_INVOKABLE QScriptValue getParamType(const QString &name);
  Q_INVOKABLE QScriptValue setParamKeyframe(const QString &name, double frame,
                                            const QScriptValue &value);
  Q_INVOKABLE QScriptValue getParamNames();

  // Properties
  Q_PROPERTY(QString type READ getType)
  QString getType() const;

  Q_PROPERTY(int paramCount READ getParamCount)
  int getParamCount() const;

  Q_PROPERTY(int inputPortCount READ getInputPortCount)
  int getInputPortCount() const;

  Q_INVOKABLE QScriptValue getInputPortName(int idx);
  Q_INVOKABLE QScriptValue connectInput(const QScriptValue &portArg,
                                        const QScriptValue &sourceArg);

  TFxP getFx() const { return m_fx; }
};

QScriptValue checkEffect(QScriptContext *context, const QScriptValue &value,
                         Effect *&out);

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::Effect *)

#endif
