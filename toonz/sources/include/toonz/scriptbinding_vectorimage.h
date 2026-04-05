#pragma once

#ifndef SCRIPTBINDING_VECTORIMAGE_H
#define SCRIPTBINDING_VECTORIMAGE_H

#include "toonz/scriptbinding.h"
#include "tvectorimage.h"

namespace TScriptBinding {

class Stroke;
class Image;

class DVAPI VectorImage final : public Wrapper {
  Q_OBJECT

  TVectorImageP m_vi;

public:
  VectorImage();
  explicit VectorImage(const TVectorImageP &vi);
  ~VectorImage();

  WRAPPER_STD_METHODS(VectorImage)
  Q_INVOKABLE QScriptValue toString();

  // Stroke operations
  Q_INVOKABLE QScriptValue addStroke(const QScriptValue &stroke);
  Q_INVOKABLE QScriptValue removeStroke(int index);
  Q_INVOKABLE QScriptValue getStroke(int index);

  // Region computation (must be called before fill on new images)
  Q_INVOKABLE QScriptValue findRegions();

  // Fill operations
  Q_INVOKABLE QScriptValue fill(double x, double y, int styleId);
  Q_INVOKABLE QScriptValue setEdgeColors(int strokeIndex, int leftColorIdx,
                                         int rightColorIdx);

  // Grouping
  Q_INVOKABLE QScriptValue group(int fromIndex, int count);
  Q_INVOKABLE QScriptValue ungroup(int index);

  // Merging
  Q_INVOKABLE QScriptValue merge(const QScriptValue &otherVi);

  // Geometric primitives (add multiple strokes forming a fillable shape)
  Q_INVOKABLE QScriptValue addRect(double x1, double y1, double x2, double y2,
                                   double thickness, int styleId);
  Q_INVOKABLE QScriptValue addCircle(double cx, double cy, double radius,
                                     double thickness, int styleId,
                                     int segments = 16);
  Q_INVOKABLE QScriptValue addPolygon(double cx, double cy, double radius,
                                      int sides, double thickness, int styleId);
  Q_INVOKABLE QScriptValue addEllipse(double cx, double cy, double rx,
                                      double ry, double thickness, int styleId,
                                      int segments = 16);
  Q_INVOKABLE QScriptValue addLine(double x1, double y1, double x2, double y2,
                                   double thickness, int styleId);

  // Filled geometric primitives (strokes + auto-fill in one call)
  Q_INVOKABLE QScriptValue addFilledRect(double x1, double y1, double x2,
                                         double y2, double thickness,
                                         int inkStyleId, int fillStyleId);
  Q_INVOKABLE QScriptValue addFilledCircle(double cx, double cy, double radius,
                                           double thickness, int inkStyleId,
                                           int fillStyleId, int segments = 16);
  Q_INVOKABLE QScriptValue addFilledPolygon(double cx, double cy, double radius,
                                            int sides, double thickness,
                                            int inkStyleId, int fillStyleId);
  Q_INVOKABLE QScriptValue addFilledEllipse(double cx, double cy, double rx,
                                            double ry, double thickness,
                                            int inkStyleId, int fillStyleId,
                                            int segments = 16);

  // Palette
  Q_INVOKABLE QScriptValue setPalette(const QScriptValue &paletteArg);

  // Convert to Image wrapper for use with Level.setFrame
  Q_INVOKABLE QScriptValue toImage();

  // Properties
  Q_PROPERTY(int strokeCount READ getStrokeCount)
  int getStrokeCount() const;

  Q_PROPERTY(int regionCount READ getRegionCount)
  int getRegionCount() const;

  // Access underlying
  TVectorImageP getVectorImage() const { return m_vi; }
};

QScriptValue checkVectorImage(QScriptContext *context,
                              const QScriptValue &value, VectorImage *&out);

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::VectorImage *)

#endif
