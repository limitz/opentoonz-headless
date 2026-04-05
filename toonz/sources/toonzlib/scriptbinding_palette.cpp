

#include "toonz/scriptbinding_palette.h"
#include "tcolorstyles.h"

namespace TScriptBinding {

Palette::Palette() : m_palette(new TPalette()) { m_palette->addRef(); }

Palette::Palette(TPalette *palette) : m_palette(palette) {
  if (m_palette) m_palette->addRef();
}

Palette::~Palette() {
  if (m_palette) m_palette->release();
}

QScriptValue Palette::toString() {
  return QString("Palette[%1 styles]").arg(m_palette->getStyleCount());
}

QScriptValue Palette::ctor(QScriptContext *context, QScriptEngine *engine) {
  return create(engine, new Palette());
}

QScriptValue Palette::addColor(int r, int g, int b, int a) {
  if (r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255 || a < 0 ||
      a > 255) {
    return context()->throwError(
        tr("Color components must be in range [0, 255]"));
  }

  TPixel32 color(r, g, b, a);

  // Ensure there's at least one page
  if (m_palette->getPageCount() == 0) {
    m_palette->addPage(L"colors");
  }

  // addStyle returns the global style ID
  int styleId = m_palette->addStyle(color);

  // Also add to the last page for organization
  TPalette::Page *page = m_palette->getPage(m_palette->getPageCount() - 1);
  page->addStyle(styleId);

  return QScriptValue(styleId);
}

QScriptValue Palette::setStyleColor(int styleIdx, int r, int g, int b,
                                    int a) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range [0, %2)")
            .arg(styleIdx)
            .arg(m_palette->getStyleCount()));
  }
  if (r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255 || a < 0 ||
      a > 255) {
    return context()->throwError(
        tr("Color components must be in range [0, 255]"));
  }

  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (style) {
    style->setMainColor(TPixel32(r, g, b, a));
  }
  return context()->thisObject();
}

QScriptValue Palette::getStyleColor(int styleIdx) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }

  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));

  TPixel32 color = style->getMainColor();
  QScriptValue obj = engine()->newObject();
  obj.setProperty("r", color.r);
  obj.setProperty("g", color.g);
  obj.setProperty("b", color.b);
  obj.setProperty("a", color.m);
  return obj;
}

QScriptValue Palette::addPage(const QString &name) {
  m_palette->addPage(name.toStdWString());
  return context()->thisObject();
}

int Palette::getStyleCount() const { return m_palette->getStyleCount(); }

int Palette::getPageCount() const { return m_palette->getPageCount(); }

QScriptValue checkPalette(QScriptContext *context, const QScriptValue &value,
                          Palette *&out) {
  out = qscriptvalue_cast<Palette *>(value);
  if (!out)
    return context->throwError(QObject::tr("Expected a Palette object"));
  return QScriptValue();
}

}  // namespace TScriptBinding
