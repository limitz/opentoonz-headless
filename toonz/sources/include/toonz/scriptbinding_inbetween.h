#pragma once

#ifndef SCRIPTBINDING_INBETWEEN_H
#define SCRIPTBINDING_INBETWEEN_H

#include "toonz/scriptbinding.h"
#include "tinbetween.h"
#include "tvectorimage.h"

namespace TScriptBinding {

class DVAPI Inbetween final : public Wrapper {
  Q_OBJECT

  TVectorImageP m_firstImage;
  TVectorImageP m_lastImage;

public:
  Inbetween();
  ~Inbetween();

  WRAPPER_STD_METHODS(Inbetween)
  Q_INVOKABLE QScriptValue toString();

  Q_INVOKABLE QScriptValue tween(double t, const QString &easing = "linear");
};

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::Inbetween *)

#endif
