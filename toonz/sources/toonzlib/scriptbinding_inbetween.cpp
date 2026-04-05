

#include "toonz/scriptbinding_inbetween.h"
#include "toonz/scriptbinding_image.h"

namespace TScriptBinding {

Inbetween::Inbetween() {}

Inbetween::~Inbetween() {}

QScriptValue Inbetween::toString() { return "Inbetween"; }

QScriptValue Inbetween::ctor(QScriptContext *context, QScriptEngine *engine) {
  QScriptValue err = checkArgumentCount(context, "Inbetween", 2);
  if (err.isError()) return err;

  Image *img1 = qscriptvalue_cast<Image *>(context->argument(0));
  Image *img2 = qscriptvalue_cast<Image *>(context->argument(1));

  if (!img1 || !img2) {
    return context->throwError(
        QObject::tr("Inbetween requires two Image arguments"));
  }

  TVectorImageP vi1 = img1->getImg();
  TVectorImageP vi2 = img2->getImg();

  if (!vi1 || !vi2) {
    return context->throwError(
        QObject::tr("Both images must be vector images"));
  }

  Inbetween *obj   = new Inbetween();
  obj->m_firstImage = vi1;
  obj->m_lastImage  = vi2;
  return create(engine, obj);
}

QScriptValue Inbetween::tween(double t, const QString &easing) {
  if (!m_firstImage || !m_lastImage) {
    return context()->throwError(tr("Inbetween not properly initialized"));
  }
  if (t < 0.0 || t > 1.0) {
    return context()->throwError(
        tr("Parameter t must be in range [0, 1], got %1").arg(t));
  }

  TInbetween inbetween(m_firstImage, m_lastImage);

  // Apply easing
  QString easeLower = easing.toLower();
  TInbetween::TweenAlgorithm algo;
  if (easeLower == "linear")
    algo = TInbetween::LinearInterpolation;
  else if (easeLower == "easein")
    algo = TInbetween::EaseInInterpolation;
  else if (easeLower == "easeout")
    algo = TInbetween::EaseOutInterpolation;
  else if (easeLower == "easeinout")
    algo = TInbetween::EaseInOutInterpolation;
  else {
    return context()->throwError(
        tr("Unknown easing '%1'. Valid: linear, easeIn, easeOut, easeInOut")
            .arg(easing));
  }

  double easedT = TInbetween::interpolation(t, algo);
  TVectorImageP result = inbetween.tween(easedT);
  TImageP img(result.getPointer());
  return create(new Image(img));
}

}  // namespace TScriptBinding
