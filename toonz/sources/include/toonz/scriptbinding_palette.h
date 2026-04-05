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

  // Color management
  Q_INVOKABLE QScriptValue addColor(int r, int g, int b, int a = 255);
  Q_INVOKABLE QScriptValue setStyleColor(int styleIdx, int r, int g, int b,
                                         int a = 255);
  Q_INVOKABLE QScriptValue getStyleColor(int styleIdx);

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
