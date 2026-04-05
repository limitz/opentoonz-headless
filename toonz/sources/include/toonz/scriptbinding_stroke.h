#pragma once

#ifndef SCRIPTBINDING_STROKE_H
#define SCRIPTBINDING_STROKE_H

#include "toonz/scriptbinding.h"
#include "tstroke.h"

namespace TScriptBinding {

class DVAPI Stroke final : public Wrapper {
  Q_OBJECT

  std::vector<TThickPoint> m_points;
  TStroke *m_stroke;
  int m_styleId;

public:
  Stroke();
  explicit Stroke(TStroke *stroke);
  ~Stroke();

  WRAPPER_STD_METHODS(Stroke)
  Q_INVOKABLE QScriptValue toString();

  // Building
  Q_INVOKABLE QScriptValue addPoint(double x, double y,
                                    double thickness = 1.0);
  Q_INVOKABLE QScriptValue addPoints(const QScriptValue &pointArray);
  Q_INVOKABLE QScriptValue build();
  Q_INVOKABLE QScriptValue close();

  // Style
  Q_INVOKABLE QScriptValue setStyle(int styleId);

  // Properties
  Q_PROPERTY(double length READ getLength)
  double getLength() const;

  Q_PROPERTY(int pointCount READ getPointCount)
  int getPointCount() const;

  Q_PROPERTY(int style READ getStyle WRITE setStyleProp)
  int getStyle() const;
  void setStyleProp(int v);

  // Access underlying stroke
  TStroke *getStroke();

private:
  void ensureBuilt();
};

QScriptValue checkStroke(QScriptContext *context, const QScriptValue &value,
                         Stroke *&out);

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::Stroke *)

#endif
