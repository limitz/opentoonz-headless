#pragma once

#ifndef SCRIPTBINDING_RASTERCANVAS_H
#define SCRIPTBINDING_RASTERCANVAS_H

#include "toonz/scriptbinding.h"
#include "trastercm.h"
#include "tpalette.h"

class TPalette;

namespace TScriptBinding {

class Palette;

class DVAPI RasterCanvas final : public Wrapper {
  Q_OBJECT

  TRasterCM32P m_raster;
  TPaletteP m_palette;
  int m_width, m_height;

public:
  RasterCanvas();
  RasterCanvas(int width, int height);
  ~RasterCanvas();

  WRAPPER_STD_METHODS(RasterCanvas)
  Q_INVOKABLE QScriptValue toString();

  // Drawing
  Q_INVOKABLE QScriptValue brushStroke(const QScriptValue &pointArray,
                                       int styleId, bool antialias = true);
  Q_INVOKABLE QScriptValue fill(int x, int y, int styleId);
  Q_INVOKABLE QScriptValue rectFill(int x1, int y1, int x2, int y2,
                                    int styleId);
  Q_INVOKABLE QScriptValue inkFill(int x, int y, int styleId,
                                   int searchRay = 10);
  Q_INVOKABLE QScriptValue clear();

  // Palette (optional — a default is created if not set)
  Q_INVOKABLE QScriptValue setPalette(const QScriptValue &paletteArg);

  // Convert to Image for Level.setFrame
  Q_INVOKABLE QScriptValue toImage();

  // Properties
  Q_PROPERTY(int width READ getWidth)
  int getWidth() const { return m_width; }

  Q_PROPERTY(int height READ getHeight)
  int getHeight() const { return m_height; }

  TRasterCM32P getRaster() const { return m_raster; }
};

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::RasterCanvas *)

#endif
