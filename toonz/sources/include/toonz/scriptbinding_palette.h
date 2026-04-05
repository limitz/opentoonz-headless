#pragma once

#ifndef SCRIPTBINDING_PALETTE_H
#define SCRIPTBINDING_PALETTE_H

#include "toonz/scriptbinding.h"
#include "tpalette.h"

namespace TScriptBinding {

class DVAPI Palette final : public Wrapper {
  Q_OBJECT

  TPalette *m_palette;

public:
  Palette();
  explicit Palette(TPalette *palette);
  ~Palette();

  WRAPPER_STD_METHODS(Palette)
  Q_INVOKABLE QScriptValue toString();

  // Color management (solid colors)
  Q_INVOKABLE QScriptValue addColor(int r, int g, int b, int a = 255);
  Q_INVOKABLE QScriptValue setStyleColor(int styleIdx, int r, int g, int b,
                                         int a = 255);
  Q_INVOKABLE QScriptValue getStyleColor(int styleIdx);

  // Style system (gradients, patterns, textures, decorative strokes, etc.)
  Q_INVOKABLE QScriptValue addStyle(int tagId);
  Q_INVOKABLE QScriptValue getStyleType(int styleIdx);
  Q_INVOKABLE QScriptValue getStyleParamCount(int styleIdx);
  Q_INVOKABLE QScriptValue getStyleParamNames(int styleIdx);
  Q_INVOKABLE QScriptValue setStyleParam(int styleIdx, int paramIdx,
                                         const QScriptValue &value);
  Q_INVOKABLE QScriptValue getStyleParam(int styleIdx, int paramIdx);
  Q_INVOKABLE QScriptValue getStyleColorParamCount(int styleIdx);
  Q_INVOKABLE QScriptValue setStyleColorParam(int styleIdx, int colorIdx,
                                              int r, int g, int b,
                                              int a = 255);
  Q_INVOKABLE QScriptValue getStyleColorParam(int styleIdx, int colorIdx);
  Q_INVOKABLE QScriptValue getAvailableTags();

  // Color model (reference image)
  Q_INVOKABLE QScriptValue loadColorModel(const QScriptValue &pathArg);
  Q_INVOKABLE QScriptValue pickColorFromModel(int x, int y);
  Q_INVOKABLE QScriptValue removeColorModel();

  // Page management
  Q_INVOKABLE QScriptValue addPage(const QString &name);

  // Properties
  Q_PROPERTY(int styleCount READ getStyleCount)
  int getStyleCount() const;

  Q_PROPERTY(int pageCount READ getPageCount)
  int getPageCount() const;

  // Access underlying
  TPalette *getPalette() const { return m_palette; }
};

QScriptValue checkPalette(QScriptContext *context, const QScriptValue &value,
                          Palette *&out);

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::Palette *)

#endif
