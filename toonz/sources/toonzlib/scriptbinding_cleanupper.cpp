

#include "toonz/scriptbinding_cleanupper.h"
#include "toonz/scriptbinding_image.h"
#include "toonz/scriptbinding_level.h"
#include "toonz/tcleanupper.h"
#include "toonz/cleanupparameters.h"
#include "trasterimage.h"
#include "ttoonzimage.h"
#include "tpalette.h"
#include "tcolorstyles.h"

namespace TScriptBinding {

Cleanupper::Cleanupper()
    : m_params(std::make_unique<CleanupParameters>()) {}

Cleanupper::~Cleanupper() = default;

QScriptValue Cleanupper::toString() { return "Cleanupper"; }

QScriptValue Cleanupper::ctor(QScriptContext *context, QScriptEngine *engine) {
  return create(engine, new Cleanupper());
}

// -----------------------------------------------------------
//  process — clean up a single raster image
// -----------------------------------------------------------

QScriptValue Cleanupper::process(QScriptValue imageArg) {
  Image *img = qscriptvalue_cast<Image *>(imageArg);
  if (!img)
    return context()->throwError(tr("Argument must be an Image"));

  TImageP src = img->getImg();
  if (!src)
    return context()->throwError(tr("Image is empty"));

  TRasterImageP ri = src;
  if (!ri) {
    // If it's a ToonzRaster (colormap), render to full-color raster
    TToonzImageP ti = src;
    if (ti) {
      TRasterCM32P cmRas = ti->getRaster();
      if (cmRas) {
        TRaster32P ras(cmRas->getSize());
        ras->clear();
        TPalette *pal = ti->getPalette();
        if (pal) {
          // Render colormap to RGBA
          for (int y = 0; y < cmRas->getLy(); y++) {
            TPixelCM32 *cmPix = cmRas->pixels(y);
            TPixel32 *px      = ras->pixels(y);
            for (int x = 0; x < cmRas->getLx(); x++) {
              int inkId  = cmPix[x].getInk();
              int tone   = cmPix[x].getTone();
              TPixel32 inkColor =
                  pal->getStyle(inkId)
                      ? pal->getStyle(inkId)->getAverageColor()
                      : TPixel32::Black;
              // tone 0 = fully opaque ink, 255 = transparent
              int alpha = 255 - tone;
              px[x]     = TPixel32(inkColor.r, inkColor.g, inkColor.b, alpha);
            }
          }
        }
        ri = TRasterImageP(ras);
        ri->setDpi(72.0, 72.0);
      }
    }
  }
  if (!ri)
    return context()->throwError(
        tr("Image must be Raster or ToonzRaster type"));

  // Set up the cleanupper singleton
  TCleanupper *cleanupper = TCleanupper::instance();
  cleanupper->setParameters(m_params.get());

  // Set source DPI from image
  double dpix = 0, dpiy = 0;
  ri->getDpi(dpix, dpiy);
  if (dpix <= 0 || dpiy <= 0) {
    dpix = 72.0;
    dpiy = 72.0;
  }
  cleanupper->setSourceDpi(TPointD(dpix, dpiy));

  // Process
  TRasterImageP resampledImage;
  CleanupPreprocessedImage *processed = cleanupper->process(
      ri,              // input (released internally)
      true,            // first_image (for auto-adjust reference)
      resampledImage,  // resampled output
      false,           // isCameraTest
      false,           // returnResampled
      false,           // onlyForSwatch
      nullptr,         // aff
      nullptr          // templateForResampled
  );

  if (!processed)
    return context()->throwError(tr("Cleanup processing failed"));

  TToonzImageP result = cleanupper->finalize(processed, true);
  delete processed;

  if (!result)
    return context()->throwError(tr("Cleanup finalization failed"));

  return engine()->newQObject(new Image(result), QScriptEngine::AutoOwnership);
}

// -----------------------------------------------------------
//  processLevel — clean up all frames in a level
// -----------------------------------------------------------

QScriptValue Cleanupper::processLevel(QScriptValue levelArg) {
  Level *level = qscriptvalue_cast<Level *>(levelArg);
  if (!level)
    return context()->throwError(tr("Argument must be a Level"));

  if (level->getFrameCount() <= 0)
    return context()->throwError(tr("Level has no frames"));

  TCleanupper *cleanupper = TCleanupper::instance();
  cleanupper->setParameters(m_params.get());

  QScriptValue newLevel = create(engine(), new Level());
  QList<TFrameId> fids;
  level->getFrameIds(fids);

  bool first = true;
  for (const TFrameId &fid : fids) {
    TImageP srcImg = level->getImg(fid);
    TRasterImageP ri = srcImg;
    if (!ri) continue;

    double dpix = 0, dpiy = 0;
    ri->getDpi(dpix, dpiy);
    if (dpix <= 0 || dpiy <= 0) {
      dpix = 72.0;
      dpiy = 72.0;
    }
    cleanupper->setSourceDpi(TPointD(dpix, dpiy));

    TRasterImageP resampledImage;
    CleanupPreprocessedImage *processed = cleanupper->process(
        ri, first, resampledImage, false, false, false, nullptr, nullptr);

    if (!processed) continue;

    TToonzImageP result = cleanupper->finalize(processed, true);
    delete processed;

    if (result) {
      QScriptValue newFrame =
          engine()->newQObject(new Image(result), QScriptEngine::AutoOwnership);
      QScriptValueList args;
      args << QString::fromStdString(fid.expand()) << newFrame;
      newLevel.property("setFrame").call(newLevel, args);
    }

    first = false;
  }

  return newLevel;
}

// -----------------------------------------------------------
//  Properties
// -----------------------------------------------------------

QString Cleanupper::getLineProcessing() const {
  switch (m_params->m_lineProcessingMode) {
  case 0:
    return "none";
  case 1:
    return "greyscale";
  case 2:
    return "color";
  default:
    return "none";
  }
}

void Cleanupper::setLineProcessing(const QString &mode) {
  if (mode == "none")
    m_params->m_lineProcessingMode = 0;
  else if (mode == "greyscale")
    m_params->m_lineProcessingMode = 1;
  else if (mode == "color")
    m_params->m_lineProcessingMode = 2;
}

int Cleanupper::getSharpness() const { return (int)m_params->m_sharpness; }
void Cleanupper::setSharpness(int v) {
  m_params->m_sharpness = std::max(0, std::min(100, v));
}

int Cleanupper::getDespeckling() const { return m_params->m_despeckling; }
void Cleanupper::setDespeckling(int v) {
  m_params->m_despeckling = std::max(0, std::min(20, v));
}

QString Cleanupper::getAntialias() const {
  if (m_params->m_postAntialias) return "morphological";
  if (m_params->m_noAntialias) return "none";
  return "standard";
}

void Cleanupper::setAntialias(const QString &mode) {
  if (mode == "none") {
    m_params->m_noAntialias   = true;
    m_params->m_postAntialias = false;
  } else if (mode == "morphological") {
    m_params->m_noAntialias   = false;
    m_params->m_postAntialias = true;
  } else {
    m_params->m_noAntialias   = false;
    m_params->m_postAntialias = false;
  }
}

int Cleanupper::getAaIntensity() const { return m_params->m_aaValue; }
void Cleanupper::setAaIntensity(int v) {
  m_params->m_aaValue = std::max(0, std::min(100, v));
}

QString Cleanupper::getAutoAdjust() const {
  switch (m_params->m_autoAdjustMode) {
  case CleanupTypes::AUTO_ADJ_NONE:
    return "none";
  case CleanupTypes::AUTO_ADJ_BLACK_EQ:
    return "blackEq";
  case CleanupTypes::AUTO_ADJ_HISTOGRAM:
    return "histogram";
  case CleanupTypes::AUTO_ADJ_HISTO_L:
    return "histoL";
  default:
    return "none";
  }
}

void Cleanupper::setAutoAdjust(const QString &mode) {
  if (mode == "none")
    m_params->m_autoAdjustMode = CleanupTypes::AUTO_ADJ_NONE;
  else if (mode == "blackEq")
    m_params->m_autoAdjustMode = CleanupTypes::AUTO_ADJ_BLACK_EQ;
  else if (mode == "histogram")
    m_params->m_autoAdjustMode = CleanupTypes::AUTO_ADJ_HISTOGRAM;
  else if (mode == "histoL")
    m_params->m_autoAdjustMode = CleanupTypes::AUTO_ADJ_HISTO_L;
}

int Cleanupper::getRotate() const { return m_params->m_rotate; }
void Cleanupper::setRotate(int deg) {
  // Only 0, 90, 180, 270 allowed
  deg = ((deg % 360) + 360) % 360;
  if (deg != 0 && deg != 90 && deg != 180 && deg != 270) deg = 0;
  m_params->m_rotate = deg;
}

bool Cleanupper::getFlipX() const { return m_params->m_flipx; }
void Cleanupper::setFlipX(bool v) { m_params->m_flipx = v; }

bool Cleanupper::getFlipY() const { return m_params->m_flipy; }
void Cleanupper::setFlipY(bool v) { m_params->m_flipy = v; }

}  // namespace TScriptBinding
