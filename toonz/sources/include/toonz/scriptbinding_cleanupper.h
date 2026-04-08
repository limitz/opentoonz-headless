#pragma once
#ifndef SCRIPTBINDING_CLEANUPPER_H
#define SCRIPTBINDING_CLEANUPPER_H

#include "toonz/scriptbinding.h"
#include <memory>

class CleanupParameters;

namespace TScriptBinding {

class DVAPI Cleanupper final : public Wrapper {
  Q_OBJECT
  std::unique_ptr<CleanupParameters> m_params;

public:
  Cleanupper();
  ~Cleanupper();

  WRAPPER_STD_METHODS(Cleanupper)
  Q_INVOKABLE QScriptValue toString();

  // Process a single raster image -> cleaned ToonzRaster image
  Q_INVOKABLE QScriptValue process(QScriptValue imageArg);

  // Process all frames in a raster level -> cleaned level
  Q_INVOKABLE QScriptValue processLevel(QScriptValue levelArg);

  // --- Properties ---

  Q_PROPERTY(QString lineProcessing READ getLineProcessing WRITE
                 setLineProcessing)
  QString getLineProcessing() const;
  void setLineProcessing(const QString &mode);

  Q_PROPERTY(int sharpness READ getSharpness WRITE setSharpness)
  int getSharpness() const;
  void setSharpness(int v);

  Q_PROPERTY(int despeckling READ getDespeckling WRITE setDespeckling)
  int getDespeckling() const;
  void setDespeckling(int v);

  Q_PROPERTY(QString antialias READ getAntialias WRITE setAntialias)
  QString getAntialias() const;
  void setAntialias(const QString &mode);

  Q_PROPERTY(int aaIntensity READ getAaIntensity WRITE setAaIntensity)
  int getAaIntensity() const;
  void setAaIntensity(int v);

  Q_PROPERTY(QString autoAdjust READ getAutoAdjust WRITE setAutoAdjust)
  QString getAutoAdjust() const;
  void setAutoAdjust(const QString &mode);

  Q_PROPERTY(int rotate READ getRotate WRITE setRotate)
  int getRotate() const;
  void setRotate(int deg);

  Q_PROPERTY(bool flipX READ getFlipX WRITE setFlipX)
  bool getFlipX() const;
  void setFlipX(bool v);

  Q_PROPERTY(bool flipY READ getFlipY WRITE setFlipY)
  bool getFlipY() const;
  void setFlipY(bool v);
};

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::Cleanupper *)

#endif
