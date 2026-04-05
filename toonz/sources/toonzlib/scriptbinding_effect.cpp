

#include "toonz/scriptbinding_effect.h"
#include "tdoubleparam.h"
#include "tdoublekeyframe.h"
#include "tparamcontainer.h"

namespace TScriptBinding {

Effect::Effect() {}

Effect::Effect(const TFxP &fx) : m_fx(fx) {}

Effect::~Effect() {}

QScriptValue Effect::toString() {
  if (!m_fx) return "Effect[null]";
  return QString("Effect[%1]")
      .arg(QString::fromStdString(m_fx->getFxType()));
}

QScriptValue Effect::ctor(QScriptContext *context, QScriptEngine *engine) {
  QScriptValue err = checkArgumentCount(context, "Effect", 1);
  if (err.isError()) return err;

  QString fxType = context->argument(0).toString();
  TFx *fx        = TFx::create(fxType.toStdString());
  if (!fx) {
    return context->throwError(
        QObject::tr("Unknown effect type '%1'").arg(fxType));
  }

  // Verify the created effect actually matches the requested type
  std::string actualType = fx->getFxType();
  if (actualType != fxType.toStdString()) {
    delete fx;
    return context->throwError(
        QObject::tr("Unknown effect type '%1'").arg(fxType));
  }

  return create(engine, new Effect(TFxP(fx)));
}

QScriptValue Effect::setParam(const QString &name, double value) {
  if (!m_fx) return context()->throwError(tr("Effect is null"));

  TParamContainer *params = m_fx->getParams();
  TParam *param = params->getParam(name.toStdString());
  if (!param) {
    return context()->throwError(
        tr("Unknown parameter '%1'").arg(name));
  }

  TDoubleParam *dp = dynamic_cast<TDoubleParam *>(param);
  if (!dp) {
    return context()->throwError(
        tr("Parameter '%1' is not a numeric parameter").arg(name));
  }

  dp->setDefaultValue(value);
  return context()->thisObject();
}

QScriptValue Effect::getParam(const QString &name) {
  if (!m_fx) return context()->throwError(tr("Effect is null"));

  TParamContainer *params = m_fx->getParams();
  TParam *param = params->getParam(name.toStdString());
  if (!param) {
    return context()->throwError(
        tr("Unknown parameter '%1'").arg(name));
  }

  TDoubleParam *dp = dynamic_cast<TDoubleParam *>(param);
  if (!dp) {
    return context()->throwError(
        tr("Parameter '%1' is not a numeric parameter").arg(name));
  }

  return QScriptValue(dp->getDefaultValue());
}

QScriptValue Effect::setParamKeyframe(const QString &name, double frame,
                                      double value) {
  if (!m_fx) return context()->throwError(tr("Effect is null"));

  TParamContainer *params = m_fx->getParams();
  TParam *param = params->getParam(name.toStdString());
  if (!param) {
    return context()->throwError(
        tr("Unknown parameter '%1'").arg(name));
  }

  TDoubleParam *dp = dynamic_cast<TDoubleParam *>(param);
  if (!dp) {
    return context()->throwError(
        tr("Parameter '%1' is not a numeric parameter").arg(name));
  }

  TDoubleKeyframe kf(frame, value);
  kf.m_type = TDoubleKeyframe::Linear;
  dp->setKeyframe(kf);
  return context()->thisObject();
}

QScriptValue Effect::getParamNames() {
  if (!m_fx) return context()->throwError(tr("Effect is null"));

  TParamContainer *params = m_fx->getParams();
  int count               = params->getParamCount();
  QScriptValue arr        = engine()->newArray(count);

  for (int i = 0; i < count; i++) {
    std::string name = params->getParamName(i);
    arr.setProperty(i, QString::fromStdString(name));
  }

  return arr;
}

QString Effect::getType() const {
  if (!m_fx) return "";
  return QString::fromStdString(m_fx->getFxType());
}

int Effect::getParamCount() const {
  if (!m_fx) return 0;
  return m_fx->getParams()->getParamCount();
}

QScriptValue checkEffect(QScriptContext *context, const QScriptValue &value,
                         Effect *&out) {
  out = qscriptvalue_cast<Effect *>(value);
  if (!out)
    return context->throwError(QObject::tr("Expected an Effect object"));
  return QScriptValue();
}

}  // namespace TScriptBinding
