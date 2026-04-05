

#include "toonz/scriptbinding_palette.h"
#include "toonz/scriptbinding_files.h"
#include "tcolorstyles.h"
#include "timage_io.h"
#include "trasterimage.h"
#include "tsystem.h"

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

QScriptValue Palette::addStyle(int tagId) {
  TColorStyle *style = TColorStyle::create(tagId);
  if (!style) {
    return context()->throwError(
        tr("Unknown style tag ID %1. Use getAvailableTags() to list valid IDs.")
            .arg(tagId));
  }

  if (m_palette->getPageCount() == 0) {
    m_palette->addPage(L"colors");
  }

  int styleId = m_palette->addStyle(style);
  TPalette::Page *page = m_palette->getPage(m_palette->getPageCount() - 1);
  page->addStyle(styleId);

  return QScriptValue(styleId);
}

QScriptValue Palette::getStyleType(int styleIdx) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }
  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));

  QScriptValue obj = engine()->newObject();
  obj.setProperty("tagId", style->getTagId());
  obj.setProperty("description",
                  style->getDescription());
  obj.setProperty("isRegionStyle", style->isRegionStyle());
  obj.setProperty("isStrokeStyle", style->isStrokeStyle());
  return obj;
}

QScriptValue Palette::getStyleParamCount(int styleIdx) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }
  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));
  return QScriptValue(style->getParamCount());
}

QScriptValue Palette::getStyleParamNames(int styleIdx) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }
  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));

  int count = style->getParamCount();
  QScriptValue arr = engine()->newArray(count);
  for (int i = 0; i < count; i++) {
    QScriptValue param = engine()->newObject();
    param.setProperty("name", style->getParamNames(i));
    int ptype = style->getParamType(i);
    QString typeStr;
    switch (ptype) {
    case TColorStyle::BOOL: typeStr = "bool"; break;
    case TColorStyle::INT: typeStr = "int"; break;
    case TColorStyle::ENUM: typeStr = "enum"; break;
    case TColorStyle::DOUBLE: typeStr = "double"; break;
    case TColorStyle::FILEPATH: typeStr = "filepath"; break;
    default: typeStr = "unknown"; break;
    }
    param.setProperty("type", typeStr);
    arr.setProperty(i, param);
  }
  return arr;
}

QScriptValue Palette::setStyleParam(int styleIdx, int paramIdx,
                                    const QScriptValue &value) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }
  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));

  if (paramIdx < 0 || paramIdx >= style->getParamCount()) {
    return context()->throwError(
        tr("Param index %1 out of range [0, %2)")
            .arg(paramIdx)
            .arg(style->getParamCount()));
  }

  TColorStyle::ParamType ptype = style->getParamType(paramIdx);
  switch (ptype) {
  case TColorStyle::BOOL:
    style->setParamValue(paramIdx, value.toBool());
    break;
  case TColorStyle::INT:
  case TColorStyle::ENUM:
    style->setParamValue(paramIdx, value.toInt32());
    break;
  case TColorStyle::DOUBLE:
    style->setParamValue(paramIdx, value.toNumber());
    break;
  case TColorStyle::FILEPATH:
    style->setParamValue(paramIdx,
                         TFilePath(value.toString().toStdWString()));
    break;
  default:
    return context()->throwError(tr("Unknown param type"));
  }

  style->invalidateIcon();
  return context()->thisObject();
}

QScriptValue Palette::getStyleParam(int styleIdx, int paramIdx) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }
  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));

  if (paramIdx < 0 || paramIdx >= style->getParamCount()) {
    return context()->throwError(
        tr("Param index %1 out of range [0, %2)")
            .arg(paramIdx)
            .arg(style->getParamCount()));
  }

  TColorStyle::ParamType ptype = style->getParamType(paramIdx);
  switch (ptype) {
  case TColorStyle::BOOL:
    return QScriptValue(style->getParamValue(TColorStyle::bool_tag(), paramIdx));
  case TColorStyle::INT:
  case TColorStyle::ENUM:
    return QScriptValue(style->getParamValue(TColorStyle::int_tag(), paramIdx));
  case TColorStyle::DOUBLE:
    return QScriptValue(
        style->getParamValue(TColorStyle::double_tag(), paramIdx));
  case TColorStyle::FILEPATH:
    return QScriptValue(QString::fromStdWString(
        style->getParamValue(TColorStyle::TFilePath_tag(), paramIdx)
            .getWideString()));
  default:
    return context()->throwError(tr("Unknown param type"));
  }
}

QScriptValue Palette::getStyleColorParamCount(int styleIdx) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }
  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));
  return QScriptValue(style->getColorParamCount());
}

QScriptValue Palette::setStyleColorParam(int styleIdx, int colorIdx, int r,
                                         int g, int b, int a) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }
  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));

  if (colorIdx < 0 || colorIdx >= style->getColorParamCount()) {
    return context()->throwError(
        tr("Color param index %1 out of range [0, %2)")
            .arg(colorIdx)
            .arg(style->getColorParamCount()));
  }

  style->setColorParamValue(colorIdx, TPixel32(r, g, b, a));
  style->invalidateIcon();
  return context()->thisObject();
}

QScriptValue Palette::getStyleColorParam(int styleIdx, int colorIdx) {
  if (styleIdx < 0 || styleIdx >= m_palette->getStyleCount()) {
    return context()->throwError(
        tr("Style index %1 out of range").arg(styleIdx));
  }
  TColorStyle *style = m_palette->getStyle(styleIdx);
  if (!style) return context()->throwError(tr("Style is null"));

  if (colorIdx < 0 || colorIdx >= style->getColorParamCount()) {
    return context()->throwError(
        tr("Color param index %1 out of range [0, %2)")
            .arg(colorIdx)
            .arg(style->getColorParamCount()));
  }

  TPixel32 color = style->getColorParamValue(colorIdx);
  QScriptValue obj = engine()->newObject();
  obj.setProperty("r", color.r);
  obj.setProperty("g", color.g);
  obj.setProperty("b", color.b);
  obj.setProperty("a", color.m);
  return obj;
}

QScriptValue Palette::getAvailableTags() {
  std::vector<int> tags;
  TColorStyle::getAllTags(tags);
  QScriptValue arr = engine()->newArray(tags.size());
  for (int i = 0; i < (int)tags.size(); i++) {
    TColorStyle *style = TColorStyle::create(tags[i]);
    QScriptValue entry = engine()->newObject();
    entry.setProperty("tagId", tags[i]);
    if (style) {
      entry.setProperty("description", style->getDescription());
      entry.setProperty("isRegionStyle", style->isRegionStyle());
      entry.setProperty("isStrokeStyle", style->isStrokeStyle());
      entry.setProperty("paramCount", style->getParamCount());
      entry.setProperty("colorParamCount", style->getColorParamCount());
      delete style;
    }
    arr.setProperty(i, entry);
  }
  return arr;
}

QScriptValue Palette::loadColorModel(const QScriptValue &pathArg) {
  TFilePath fp;
  QScriptValue err = checkFilePath(context(), pathArg, fp);
  if (err.isError()) return err;

  if (!TSystem::doesExistFileOrLevel(fp)) {
    return context()->throwError(
        tr("File %1 doesn't exist").arg(pathArg.toString()));
  }

  try {
    TImageReaderP reader(fp);
    TImageP img = reader->load();
    if (!img) {
      return context()->throwError(
          tr("Could not load image %1").arg(pathArg.toString()));
    }
    m_palette->setRefImg(img);
    m_palette->setRefImgPath(fp);
    return context()->thisObject();
  } catch (...) {
    return context()->throwError(
        tr("Exception loading %1").arg(pathArg.toString()));
  }
}

QScriptValue Palette::pickColorFromModel(int x, int y) {
  TImageP img = m_palette->getRefImg();
  if (!img) {
    return context()->throwError(tr("No color model loaded"));
  }

  TRasterImageP ri = img;
  if (!ri || !ri->getRaster()) {
    return context()->throwError(
        tr("Color model is not a raster image"));
  }

  TRasterP raster = ri->getRaster();
  if (x < 0 || x >= raster->getLx() || y < 0 || y >= raster->getLy()) {
    return context()->throwError(
        tr("Coordinates (%1, %2) out of bounds [0-%3, 0-%4]")
            .arg(x).arg(y)
            .arg(raster->getLx() - 1).arg(raster->getLy() - 1));
  }

  // Read pixel color
  TRaster32P raster32 = raster;
  TPixel32 color;
  if (raster32) {
    color = raster32->pixels(y)[x];
  } else {
    // Try grayscale
    TRasterGR8P rasterGR = raster;
    if (rasterGR) {
      int v   = rasterGR->pixels(y)[x].value;
      color = TPixel32(v, v, v, 255);
    } else {
      return context()->throwError(tr("Unsupported raster format"));
    }
  }

  QScriptValue obj = engine()->newObject();
  obj.setProperty("r", color.r);
  obj.setProperty("g", color.g);
  obj.setProperty("b", color.b);
  obj.setProperty("a", color.m);

  // Also return closest palette style
  int closestStyle = m_palette->getClosestStyle(color);
  obj.setProperty("closestStyleId", closestStyle);

  return obj;
}

QScriptValue Palette::removeColorModel() {
  m_palette->setRefImg(TImageP());
  m_palette->setRefImgPath(TFilePath());
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
