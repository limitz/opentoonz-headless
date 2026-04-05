

#include "toonz/scriptbinding_image.h"
#include "toonz/scriptbinding_level.h"
#include "toonz/scriptbinding_files.h"
#include "tsystem.h"
#include "ttoonzimage.h"
#include "trasterimage.h"
#include "trastercm.h"
#include "tpalette.h"
#include "tfiletype.h"
#include "timage_io.h"
#include "tlevel_io.h"

namespace TScriptBinding {

Image::Image() {}

Image::Image(const TImageP img) : m_img(img) {}

Image::Image(TImage *img) : m_img(img) {}

Image::~Image() {}

QScriptValue Image::ctor(QScriptContext *context, QScriptEngine *engine) {
  Image *img       = new Image();
  QScriptValue obj = create(engine, img);
  QScriptValue err = checkArgumentCount(context, "the Image constructor", 0, 1);
  if (err.isError()) return err;
  if (context->argumentCount() == 1) {
    return obj.property("load").call(obj, context->argumentsObject());
  }
  return obj;
}

QScriptValue Image::toString() {
  if (m_img) {
    TImage::Type type = m_img->getType();
    if (type == TImage::RASTER)
      return QString("Raster image ( %1 x %2 )")
          .arg(getWidth())
          .arg(getHeight());
    else if (type == TImage::TOONZ_RASTER)
      return QString("Toonz raster image ( %1 x %2 )")
          .arg(getWidth())
          .arg(getHeight());
    else if (type == TImage::VECTOR)
      return QString("Vector image");
    else
      return QString("Image");
  } else {
    return "Empty image";
  }
}

int Image::getWidth() {
  return !!m_img && !!m_img->raster() ? m_img->raster()->getSize().lx : 0;
}

int Image::getHeight() {
  return !!m_img && !!m_img->raster() ? m_img->raster()->getSize().ly : 0;
}

double Image::getDpi() {
  if (TRasterImageP ri = m_img) {
    double dpix = 0, dpiy = 0;
    ri->getDpi(dpix, dpiy);
    return dpix;
  } else if (TToonzImageP ti = m_img) {
    double dpix = 0, dpiy = 0;
    ti->getDpi(dpix, dpiy);
    return dpix;
  } else
    return 0;
}

QString Image::getType() const {
  if (m_img) {
    TImage::Type type = m_img->getType();
    if (type == TImage::RASTER)
      return "Raster";
    else if (type == TImage::TOONZ_RASTER)
      return "ToonzRaster";
    else if (type == TImage::VECTOR)
      return "Vector";
    else
      return "Unknown";
  } else
    return "Empty";
}

QScriptValue Image::load(const QScriptValue &fpArg) {
  // clear the old image (if any)
  m_img = TImageP();

  // get the path
  TFilePath fp;
  QScriptValue err = checkFilePath(context(), fpArg, fp);
  if (err.isError()) return err;
  QString fpStr = fpArg.toString();

  try {
    // check if the file/level does exist
    if (!TSystem::doesExistFileOrLevel(fp)) {
      return context()->throwError(tr("File %1 doesn't exist").arg(fpStr));
    }

    // the file could be a level
    TFileType::Type fileType = TFileType::getInfo(fp);
    if (TFileType::isLevel(fileType)) {
      // file is a level: read first frame
      TLevelReaderP lr(fp);
      TLevelP level = lr->loadInfo();
      int n         = level->getFrameCount();
      if (n > 0) {
        // there are some frames
        TFrameId fid = fp.getFrame();
        if (fid == TFrameId::NO_FRAME || fid == TFrameId::EMPTY_FRAME)
          fid = level->begin()->first;

        m_img = lr->getFrameReader(fid)->load();
        if (!m_img) {
          return context()->throwError(QString("Could not read %1").arg(fpStr));
        }
        m_img->setPalette(level->getPalette());
        if (n > 1 && (fp.getFrame() == TFrameId::EMPTY_FRAME ||
                      fp.getFrame() == TFrameId::NO_FRAME)) {
          // warning: a multi-frame level read into an Image
          warning(tr("Loaded first frame of %1").arg(n));
        }
      } else {
        // level contains no frame (not sure it can even happen)
        return context()->throwError(
            QString("%1 contains no frames").arg(fpStr));
      }
    } else {
      // plain image: try to read it
      if (!TImageReader::load(fp, m_img)) {
        return context()->throwError(
            QString("File %1 not found or not readable").arg(fpStr));
      }
    }
    // return a reference to the Image object
    return context()->thisObject();
  } catch (...) {
    return context()->throwError(
        tr("Unexpected error while reading image").arg(fpStr));
  }
}

QScriptValue Image::save(const QScriptValue &fpArg) {
  // clear the old image (if any)
  if (!m_img) {
    return context()->throwError("Can't save an empty image");
  }

  // get the path
  TFilePath fp;
  QScriptValue err = checkFilePath(context(), fpArg, fp);
  if (err.isError()) return err;
  QString fpStr = fpArg.toString();

  // handle conversion (if it is needed and possible)
  TFileType::Type fileType = TFileType::getInfo(fp);

  bool isCompatible = false;
  if (TFileType::isFullColor(fileType)) {
    if (m_img->getType() == TImage::RASTER ||
        m_img->getType() == TImage::TOONZ_RASTER)
      isCompatible = true;
  } else if (TFileType::isVector(fileType)) {
    if (m_img->getType() == TImage::VECTOR) isCompatible = true;
  } else if (fileType & TFileType::CMAPPED_IMAGE) {
    if (m_img->getType() == TImage::TOONZ_RASTER) isCompatible = true;
  } else {
    return context()->throwError(tr("Unrecognized file type :").arg(fpStr));
  }
  if (!isCompatible) {
    return context()->throwError(
        tr("Can't save a %1 image to this file type : %2")
            .arg(getType())
            .arg(fpStr));
  }

  // Convert ToonzRaster to plain Raster for full-color output formats
  // ToonzRaster uses color-mapped pixels (TRasterCM32) which need
  // palette-based rendering to produce standard RGBA output.
  TImageP saveImg = m_img;
  if (TFileType::isFullColor(fileType) &&
      m_img->getType() == TImage::TOONZ_RASTER) {
    TToonzImageP ti = m_img;
    if (ti && ti->getRaster()) {
      TDimension size = ti->getSize();
      TRaster32P ras(size);
      ras->clear();
      TPalette *pal = ti->getPalette();
      if (pal) {
        // Render each pixel through the palette
        TRasterCM32P cmRas = ti->getRaster();
        for (int y = 0; y < size.ly; y++) {
          TPixelCM32 *cmPix = cmRas->pixels(y);
          TPixel32 *outPix  = ras->pixels(y);
          for (int x = 0; x < size.lx; x++) {
            int ink   = cmPix[x].getInk();
            int paint = cmPix[x].getPaint();
            int tone  = cmPix[x].getTone();
            TPixel32 inkColor   = pal->getStyle(ink)->getMainColor();
            TPixel32 paintColor = pal->getStyle(paint)->getMainColor();
            // tone: 0 = full ink, 255 = full paint
            if (tone == 0)
              outPix[x] = inkColor;
            else if (tone == 255)
              outPix[x] = paintColor;
            else {
              // Blend ink and paint by tone
              int t = tone, it = 255 - tone;
              outPix[x].r = (inkColor.r * it + paintColor.r * t) / 255;
              outPix[x].g = (inkColor.g * it + paintColor.g * t) / 255;
              outPix[x].b = (inkColor.b * it + paintColor.b * t) / 255;
              outPix[x].m = (inkColor.m * it + paintColor.m * t) / 255;
            }
          }
        }
      }
      TRasterImageP ri(ras);
      double dpix, dpiy;
      ti->getDpi(dpix, dpiy);
      ri->setDpi(dpix, dpiy);
      saveImg = TImageP(ri);
    }
  }

  try {
    bool isRasterFormat = TFileType::isFullColor(fileType);
    bool isSaveRaster   = saveImg->getType() == TImage::RASTER;

    if (isRasterFormat && isSaveRaster) {
      // For raster images to raster formats (PNG, TIF, etc.),
      // write directly to the exact path to avoid TFilePath frame number
      // normalization (which turns _0.png into _0001.png, etc.)
      TImageWriter::save(fp, saveImg);
    } else if (TFileType::isLevel(fileType)) {
      // Vector levels (.pli) and ToonzRaster levels (.tlv) need
      // the level writer
      TLevelP level = new TLevel();
      level->setPalette(saveImg->getPalette());
      level->setFrame(TFrameId(1), saveImg);
      TLevelWriterP lw(fp);
      if (saveImg->getPalette()) lw->setPalette(saveImg->getPalette());
      lw->save(level);
    } else {
      TImageWriterP iw(fp);
      iw->save(saveImg);
    }
    // return a reference to the Image object
    return context()->thisObject();
  } catch (...) {
    return context()->throwError(
        tr("Unexpected error while writing image").arg(fpStr));
  }
}

QScriptValue checkImage(QScriptContext *context, const QScriptValue &value,
                        Image *&img) {
  img = qscriptvalue_cast<Image *>(value);
  if (!img || !img->getImg())
    return context->throwError(
        QObject::tr("Bad argument (%1): should be an Image (not empty)")
            .arg(value.toString()));
  else
    return QScriptValue();
}

}  // namespace TScriptBinding
