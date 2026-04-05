

#include "toonz/scriptbinding_effect.h"
#include "tdoubleparam.h"
#include "tdoublekeyframe.h"
#include "tparamcontainer.h"
#include "tnotanimatableparam.h"
#include "tparamset.h"
#include "tspectrumparam.h"
#include "ttonecurveparam.h"
#include "tfilepath.h"

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

// ---------------------------------------------------------------
//  setParam — accepts number, bool, string, or array depending on
//  the underlying TParam subclass.
// ---------------------------------------------------------------

QScriptValue Effect::setParam(const QString &name, const QScriptValue &value) {
  if (!m_fx) return context()->throwError(tr("Effect is null"));

  TParamContainer *params = m_fx->getParams();
  TParam *param           = params->getParam(name.toStdString());
  if (!param) {
    return context()->throwError(tr("Unknown parameter '%1'").arg(name));
  }

  // --- Animatable numeric ---
  if (auto dp = dynamic_cast<TDoubleParam *>(param)) {
    if (!value.isNumber())
      return context()->throwError(
          tr("Parameter '%1' expects a number").arg(name));
    dp->setDefaultValue(value.toNumber());
    return context()->thisObject();
  }

  // --- Non-animatable types ---
  if (auto ip = dynamic_cast<TIntParam *>(param)) {
    if (!value.isNumber())
      return context()->throwError(
          tr("Parameter '%1' expects a number").arg(name));
    ip->setValue(value.toInt32());
    return context()->thisObject();
  }
  if (auto bp = dynamic_cast<TBoolParam *>(param)) {
    bp->setValue(value.toBool());
    return context()->thisObject();
  }
  if (auto ep = dynamic_cast<TIntEnumParam *>(param)) {
    if (!value.isNumber())
      return context()->throwError(
          tr("Parameter '%1' expects a number (enum index)").arg(name));
    ep->setValue(value.toInt32());
    return context()->thisObject();
  }
  if (auto nap = dynamic_cast<TNADoubleParam *>(param)) {
    if (!value.isNumber())
      return context()->throwError(
          tr("Parameter '%1' expects a number").arg(name));
    nap->setValue(value.toNumber());
    return context()->thisObject();
  }
  if (auto sp = dynamic_cast<TStringParam *>(param)) {
    sp->setValue(value.toString().toStdWString());
    return context()->thisObject();
  }
  if (auto fp = dynamic_cast<TFilePathParam *>(param)) {
    fp->setValue(TFilePath(value.toString().toStdWString()));
    return context()->thisObject();
  }

  // --- Animatable compound types (array input) ---
  if (auto pp = dynamic_cast<TPointParam *>(param)) {
    if (!value.isArray() || value.property("length").toUInt32() < 2)
      return context()->throwError(
          tr("Parameter '%1' expects [x, y]").arg(name));
    pp->setDefaultValue(
        TPointD(value.property(0).toNumber(), value.property(1).toNumber()));
    return context()->thisObject();
  }
  if (auto pxp = dynamic_cast<TPixelParam *>(param)) {
    if (!value.isArray() || value.property("length").toUInt32() < 3)
      return context()->throwError(
          tr("Parameter '%1' expects [r, g, b] or [r, g, b, a]").arg(name));
    int r = value.property(0).toInt32();
    int g = value.property(1).toInt32();
    int b = value.property(2).toInt32();
    int a = value.property("length").toUInt32() >= 4
                ? value.property(3).toInt32()
                : 255;
    pxp->setDefaultValue(TPixel32(r, g, b, a));
    return context()->thisObject();
  }
  if (auto rp = dynamic_cast<TRangeParam *>(param)) {
    if (!value.isArray() || value.property("length").toUInt32() < 2)
      return context()->throwError(
          tr("Parameter '%1' expects [min, max]").arg(name));
    rp->setDefaultValue(DoublePair(value.property(0).toNumber(),
                                   value.property(1).toNumber()));
    return context()->thisObject();
  }

  return context()->throwError(
      tr("Parameter '%1' has unsupported type").arg(name));
}

// ---------------------------------------------------------------
//  getParam — returns the appropriate JS type for the parameter.
// ---------------------------------------------------------------

QScriptValue Effect::getParam(const QString &name) {
  if (!m_fx) return context()->throwError(tr("Effect is null"));

  TParamContainer *params = m_fx->getParams();
  TParam *param           = params->getParam(name.toStdString());
  if (!param) {
    return context()->throwError(tr("Unknown parameter '%1'").arg(name));
  }

  if (auto dp = dynamic_cast<TDoubleParam *>(param))
    return QScriptValue(dp->getDefaultValue());
  if (auto ip = dynamic_cast<TIntParam *>(param))
    return QScriptValue(ip->getValue());
  if (auto bp = dynamic_cast<TBoolParam *>(param))
    return QScriptValue(bp->getValue());
  if (auto ep = dynamic_cast<TIntEnumParam *>(param))
    return QScriptValue(ep->getValue());
  if (auto nap = dynamic_cast<TNADoubleParam *>(param))
    return QScriptValue(nap->getValue());
  if (auto sp = dynamic_cast<TStringParam *>(param))
    return QScriptValue(QString::fromStdWString(sp->getValue()));
  if (auto fp = dynamic_cast<TFilePathParam *>(param))
    return QScriptValue(
        QString::fromStdWString(fp->getValue().getWideString()));

  if (auto pp = dynamic_cast<TPointParam *>(param)) {
    TPointD v   = pp->getDefaultValue();
    QScriptValue arr = engine()->newArray(2);
    arr.setProperty(0, v.x);
    arr.setProperty(1, v.y);
    return arr;
  }
  if (auto pxp = dynamic_cast<TPixelParam *>(param)) {
    TPixel32 v  = pxp->getDefaultValue();
    QScriptValue arr = engine()->newArray(4);
    arr.setProperty(0, v.r);
    arr.setProperty(1, v.g);
    arr.setProperty(2, v.b);
    arr.setProperty(3, v.m);
    return arr;
  }
  if (auto rp = dynamic_cast<TRangeParam *>(param)) {
    DoublePair v = rp->getDefaultValue();
    QScriptValue arr = engine()->newArray(2);
    arr.setProperty(0, v.first);
    arr.setProperty(1, v.second);
    return arr;
  }

  return context()->throwError(
      tr("Parameter '%1' has unsupported type").arg(name));
}

// ---------------------------------------------------------------
//  getParamType — returns the type name as a string.
// ---------------------------------------------------------------

QScriptValue Effect::getParamType(const QString &name) {
  if (!m_fx) return context()->throwError(tr("Effect is null"));

  TParamContainer *params = m_fx->getParams();
  TParam *param           = params->getParam(name.toStdString());
  if (!param) {
    return context()->throwError(tr("Unknown parameter '%1'").arg(name));
  }

  if (dynamic_cast<TDoubleParam *>(param)) return QScriptValue("double");
  if (dynamic_cast<TIntParam *>(param)) return QScriptValue("int");
  if (dynamic_cast<TBoolParam *>(param)) return QScriptValue("bool");
  if (dynamic_cast<TIntEnumParam *>(param)) return QScriptValue("enum");
  if (dynamic_cast<TNADoubleParam *>(param)) return QScriptValue("double");
  if (dynamic_cast<TStringParam *>(param)) return QScriptValue("string");
  if (dynamic_cast<TFilePathParam *>(param)) return QScriptValue("filepath");
  if (dynamic_cast<TPointParam *>(param)) return QScriptValue("point");
  if (dynamic_cast<TPixelParam *>(param)) return QScriptValue("pixel");
  if (dynamic_cast<TRangeParam *>(param)) return QScriptValue("range");
  if (dynamic_cast<TSpectrumParam *>(param)) return QScriptValue("spectrum");
  if (dynamic_cast<TToneCurveParam *>(param))
    return QScriptValue("tonecurve");
  return QScriptValue("unknown");
}

// ---------------------------------------------------------------
//  setParamKeyframe — for animatable types only.
// ---------------------------------------------------------------

QScriptValue Effect::setParamKeyframe(const QString &name, double frame,
                                      const QScriptValue &value) {
  if (!m_fx) return context()->throwError(tr("Effect is null"));

  TParamContainer *params = m_fx->getParams();
  TParam *param           = params->getParam(name.toStdString());
  if (!param) {
    return context()->throwError(tr("Unknown parameter '%1'").arg(name));
  }

  if (auto dp = dynamic_cast<TDoubleParam *>(param)) {
    TDoubleKeyframe kf(frame, value.toNumber());
    kf.m_type = TDoubleKeyframe::Linear;
    dp->setKeyframe(kf);
    return context()->thisObject();
  }
  if (auto pp = dynamic_cast<TPointParam *>(param)) {
    if (!value.isArray() || value.property("length").toUInt32() < 2)
      return context()->throwError(
          tr("Parameter '%1' expects [x, y]").arg(name));
    pp->setValue(frame,
                TPointD(value.property(0).toNumber(),
                        value.property(1).toNumber()));
    return context()->thisObject();
  }
  if (auto pxp = dynamic_cast<TPixelParam *>(param)) {
    if (!value.isArray() || value.property("length").toUInt32() < 3)
      return context()->throwError(
          tr("Parameter '%1' expects [r, g, b] or [r, g, b, a]").arg(name));
    int r = value.property(0).toInt32();
    int g = value.property(1).toInt32();
    int b = value.property(2).toInt32();
    int a = value.property("length").toUInt32() >= 4
                ? value.property(3).toInt32()
                : 255;
    pxp->setValue(frame, TPixel32(r, g, b, a));
    return context()->thisObject();
  }
  if (auto rp = dynamic_cast<TRangeParam *>(param)) {
    if (!value.isArray() || value.property("length").toUInt32() < 2)
      return context()->throwError(
          tr("Parameter '%1' expects [min, max]").arg(name));
    rp->setValue(frame, DoublePair(value.property(0).toNumber(),
                                  value.property(1).toNumber()));
    return context()->thisObject();
  }

  // Non-animatable types
  if (dynamic_cast<TIntParam *>(param) ||
      dynamic_cast<TBoolParam *>(param) ||
      dynamic_cast<TIntEnumParam *>(param) ||
      dynamic_cast<TNADoubleParam *>(param) ||
      dynamic_cast<TStringParam *>(param) ||
      dynamic_cast<TFilePathParam *>(param)) {
    return context()->throwError(
        tr("Parameter '%1' is not animatable — use setParam instead")
            .arg(name));
  }

  return context()->throwError(
      tr("Parameter '%1' has unsupported type for keyframing").arg(name));
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
