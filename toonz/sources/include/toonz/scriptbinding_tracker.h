#pragma once
#ifndef SCRIPTBINDING_TRACKER_H
#define SCRIPTBINDING_TRACKER_H

#include "toonz/scriptbinding.h"

namespace TScriptBinding {

class DVAPI Tracker final : public Wrapper {
  Q_OBJECT

  class Imp;
  Imp *m_imp;

public:
  Tracker();
  ~Tracker();

  WRAPPER_STD_METHODS(Tracker)
  Q_INVOKABLE QScriptValue toString();

  // Define a tracking region on the first frame image
  // Returns region index
  Q_INVOKABLE QScriptValue addRegion(int x, int y, int width, int height);

  // Track all regions across frames in a level.
  // Returns array of per-region results: [{x:[...], y:[...], status:[...]}, ...]
  Q_INVOKABLE QScriptValue track(QScriptValue levelArg, int fromFrame,
                                 int toFrame);

  // Properties
  Q_PROPERTY(double threshold READ getThreshold WRITE setThreshold)
  double getThreshold() const;
  void setThreshold(double v);

  Q_PROPERTY(double sensitivity READ getSensitivity WRITE setSensitivity)
  double getSensitivity() const;
  void setSensitivity(double v);

  Q_PROPERTY(bool variableRegion READ getVariableRegion WRITE setVariableRegion)
  bool getVariableRegion() const;
  void setVariableRegion(bool v);

  Q_PROPERTY(bool includeBackground READ getIncludeBackground WRITE
                 setIncludeBackground)
  bool getIncludeBackground() const;
  void setIncludeBackground(bool v);
};

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::Tracker *)

#endif
