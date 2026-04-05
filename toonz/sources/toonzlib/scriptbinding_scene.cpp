

#include "toonz/scriptbinding_scene.h"
#include "toonz/scriptbinding_level.h"
#include "toonz/scriptbinding_files.h"
#include "toonz/scriptbinding_stageobject.h"
#include "toonz/scriptbinding_effect.h"
#include "toonz/scriptbinding_image.h"
#include "toonz/txshleveltypes.h"
#include "toonz/levelproperties.h"
#include "toonz/txshsimplelevel.h"

#include "tsystem.h"
#include "tfiletype.h"
#include "trasterimage.h"
#include "ttoonzimage.h"
#include "tmeshimage.h"
#include "ext/meshbuilder.h"
#include "ext/meshutils.h"

#include "toonz/tproject.h"
#include "toonz/toonzscene.h"
#include "toonz/txsheet.h"
#include "toonz/txshcell.h"
#include "toonz/txshcolumn.h"
#include "toonz/levelset.h"
#include "toonz/tstageobjecttree.h"
#include "toonz/sceneproperties.h"
#include "toonz/fxdag.h"
#include "toonz/tcolumnfxset.h"
#include "tfx.h"
#include "toutputproperties.h"
#include "toonz/tcamera.h"
#include "toonz/tstageobjectspline.h"
#include "tstroke.h"

namespace TScriptBinding {

Scene::Scene() {
  m_scene = new ToonzScene();
  TProjectManager::instance()->initializeScene(m_scene);
}

Scene::~Scene() { delete m_scene; }

QScriptValue Scene::ctor(QScriptContext *context, QScriptEngine *engine) {
  QScriptValue obj = create(engine, new Scene());
  if (context->argumentCount() == 1) {
    return obj.property("load").call(obj, context->argumentsObject());
  }
  return obj;
}

QScriptValue Scene::toString() {
  return QString("Scene (%1 frames)").arg(getFrameCount());
}

int Scene::getFrameCount() { return m_scene->getFrameCount(); }

int Scene::getColumnCount() { return m_scene->getXsheet()->getColumnCount(); }

QScriptValue Scene::load(const QScriptValue &fpArg) {
  TFilePath fp;
  QScriptValue err = checkFilePath(context(), fpArg, fp);
  if (err.isError()) return err;
  if (!fp.isAbsolute())
    fp = TProjectManager::instance()->getCurrentProject()->getScenesPath() + fp;
  try {
    if (!TSystem::doesExistFileOrLevel(fp)) {
      return context()->throwError(
          tr("File %1 doesn't exist").arg(fpArg.toString()));
    }
    m_scene->load(fp);
    return context()->thisObject();
  } catch (...) {
    return context()->throwError(
        tr("Exception reading %1").arg(fpArg.toString()));
  }
}

QScriptValue Scene::save(const QScriptValue &fpArg) {
  TFilePath fp;
  QScriptValue err = checkFilePath(context(), fpArg, fp);
  if (err.isError()) return err;
  if (!fp.isAbsolute())
    fp = TProjectManager::instance()->getCurrentProject()->getScenesPath() + fp;
  try {
    m_scene->save(fp);
    return context()->thisObject();
  } catch (...) {
    return context()->throwError(
        tr("Exception writing %1").arg(fpArg.toString()));
  }
}

QScriptValue Scene::getLevels() const {
  QScriptValue result = engine()->newArray();
  qint32 index        = 0;
  std::vector<TXshLevel *> levels;
  m_scene->getLevelSet()->listLevels(levels);
  for (std::vector<TXshLevel *>::iterator it = levels.begin();
       it != levels.end(); ++it) {
    TXshSimpleLevel *sl = (*it)->getSimpleLevel();
    if (sl) {
      Level *level = new Level(sl);
      result.setProperty(index++, create(engine(), level));
    }
  }
  return result;
}

QScriptValue Scene::getLevel(const QString &name) const {
  TXshLevel *xl       = m_scene->getLevelSet()->getLevel(name.toStdWString());
  TXshSimpleLevel *sl = xl ? xl->getSimpleLevel() : 0;
  if (sl) {
    Level *level = new Level(sl);
    return create(engine(), level);
  } else
    return QScriptValue();
}

QScriptValue Scene::newLevel(const QString &levelTypeStr,
                             const QString &levelName) const {
  if (levelName.isEmpty()) {
    return context()->throwError(tr("Level name cannot be empty"));
  }

  int levelType = NO_XSHLEVEL;
  if (levelTypeStr == "Vector")
    levelType = PLI_XSHLEVEL;
  else if (levelTypeStr == "ToonzRaster")
    levelType = TZP_XSHLEVEL;
  else if (levelTypeStr == "Raster")
    levelType = OVL_XSHLEVEL;
  if (levelType == NO_XSHLEVEL)
    return context()->throwError(
        tr("Bad level type (%1): must be Vector,Raster or ToonzRaster")
            .arg(levelTypeStr));

  if (m_scene->getLevelSet()->hasLevel(levelName.toStdWString()))
    return context()->throwError(
        tr("Can't add the level: name(%1) is already used").arg(levelName));

  TXshLevel *xl = m_scene->createNewLevel(levelType, levelName.toStdWString());
  xl->getSimpleLevel()->setDirtyFlag(true);
  return create(engine(), new Level(xl->getSimpleLevel()));
}

QScriptValue Scene::loadLevel(const QString &levelName,
                              const QScriptValue &fpArg) const {
  if (m_scene->getLevelSet()->hasLevel(levelName.toStdWString()))
    return context()->throwError(
        tr("Can't add the level: name(%1) is already used").arg(levelName));
  TFilePath fp;
  QScriptValue err = checkFilePath(context(), fpArg, fp);
  if (err.isError()) return err;
  TFileType::Type type = TFileType::getInfo(fp);
  if ((type & TFileType::VIEWABLE) == 0)
    return context()->throwError(
        tr("Can't load this kind of file as a level : %1")
            .arg(fpArg.toString()));
  TXshLevel *xl = m_scene->loadLevel(fp);
  if (!xl || !xl->getSimpleLevel())
    return context()->throwError(
        tr("Could not load level %1").arg(fpArg.toString()));
  return create(engine(), new Level(xl->getSimpleLevel()));
}

QString Scene::doSetCell(int row, int col, const QScriptValue &levelArg,
                         const QScriptValue &fidArg) {
  if (row < 0 || col < 0) {
    return "Bad row/col values";
  }

  QString err;
  TXshCell cell;
  cell.m_frameId = Level::getFid(fidArg, err);
  if (err != "") return err;
  Level *level = qscriptvalue_cast<Level *>(levelArg);
  if (level) {
    TXshSimpleLevel *sl = level->getSimpleLevel();
    TXshLevel *xl       = m_scene->getLevelSet()->getLevel(sl->getName());
    if (!xl || xl->getSimpleLevel() != sl) {
      return tr("Level is not included in the scene : %1")
          .arg(levelArg.toString());
    }
    cell.m_level = sl;
  } else {
    if (!levelArg.isString())
      return tr("%1 : Expected a Level instance or a level name")
          .arg(levelArg.toString());
    QString levelName = levelArg.toString();
    TXshLevel *xl = m_scene->getLevelSet()->getLevel(levelName.toStdWString());
    if (!xl)
      return tr("Level '%1' is not included in the scene").arg(levelName);
    cell.m_level = xl;
  }
  m_scene->getXsheet()->setCell(row, col, cell);
  return "";
}

QScriptValue Scene::setCell(int row, int col, const QScriptValue &level,
                            const QScriptValue &fid) {
  QString err = doSetCell(row, col, level, fid);
  if (err != "") return context()->throwError(err);
  return context()->thisObject();
}

QScriptValue Scene::setCell(int row, int col, const QScriptValue &cellArg) {
  if (cellArg.isUndefined()) {
    if (row >= 0 && col >= 0)
      m_scene->getXsheet()->setCell(row, col, TXshCell());
  } else {
    if (!cellArg.isObject() || cellArg.property("level").isUndefined() ||
        cellArg.property("fid").isUndefined())
      return context()->throwError(
          "Third argument should be an object with attributes 'level' and "
          "'fid'");
    QScriptValue levelArg = cellArg.property("level");
    QScriptValue fidArg   = cellArg.property("fid");
    QString err           = doSetCell(row, col, levelArg, fidArg);
    if (err != "") return context()->throwError(err);
  }
  return context()->thisObject();
}

QScriptValue Scene::getCell(int row, int col) {
  TXshCell cell       = m_scene->getXsheet()->getCell(row, col);
  TXshSimpleLevel *sl = cell.getSimpleLevel();
  if (sl) {
    QScriptValue level = create(engine(), new Level(sl));
    QScriptValue fid;
    if (cell.m_frameId.getLetter().isEmpty())
      fid = cell.m_frameId.getNumber();
    else
      fid = QString::fromStdString(cell.m_frameId.expand());
    QScriptValue result = engine()->newObject();
    result.setProperty("level", level);
    result.setProperty("fid", fid);
    return result;
  } else {
    return QScriptValue();
  }
}

QScriptValue Scene::insertColumn(int col) {
  m_scene->getXsheet()->insertColumn(col);
  return context()->thisObject();
}

QScriptValue Scene::deleteColumn(int col) {
  m_scene->getXsheet()->removeColumn(col);
  return context()->thisObject();
}

QScriptValue Scene::getStageObject(int colIdx) {
  if (colIdx < 0) {
    return context()->throwError(
        tr("Column index must be >= 0, got %1").arg(colIdx));
  }
  TXsheet *xsh = m_scene->getXsheet();
  TStageObjectId id = TStageObjectId::ColumnId(colIdx);
  TStageObjectTree *tree = xsh->getStageObjectTree();
  TStageObject *obj      = tree->getStageObject(id, true);
  if (!obj) {
    return context()->throwError(
        tr("Cannot get stage object for column %1").arg(colIdx));
  }
  return create(new StageObject(obj, tree));
}

QScriptValue Scene::connectEffect(int colIdx, const QScriptValue &effectArg) {
  Effect *eff = nullptr;
  QScriptValue err = checkEffect(context(), effectArg, eff);
  if (err.isError()) return err;

  TXsheet *xsh = m_scene->getXsheet();
  if (colIdx < 0 || colIdx >= xsh->getColumnCount()) {
    return context()->throwError(
        tr("Column index %1 out of range [0, %2)")
            .arg(colIdx)
            .arg(xsh->getColumnCount()));
  }

  TXshColumn *col = xsh->getColumn(colIdx);
  if (!col) {
    return context()->throwError(
        tr("Column %1 does not exist").arg(colIdx));
  }

  TFx *columnFx = col->getFx();
  if (!columnFx) {
    return context()->throwError(
        tr("Column %1 has no FX node").arg(colIdx));
  }

  TFxP fx = eff->getFx();
  if (!fx) {
    return context()->throwError(tr("Effect is null"));
  }

  FxDag *fxDag = xsh->getFxDag();

  // Assign unique ID and register in the DAG
  fxDag->assignUniqueId(fx.getPointer());
  fxDag->getInternalFxs()->addFx(fx.getPointer());

  // Wire: column FX -> effect's first input port
  if (fx->getInputPortCount() > 0) {
    fx->getInputPort(0)->setFx(columnFx);
  } else {
    return context()->throwError(
        tr("Effect '%1' has no input ports")
            .arg(QString::fromStdString(fx->getFxType())));
  }

  // Disconnect column from xsheet output (if connected) and connect effect
  fxDag->removeFromXsheet(columnFx);
  fxDag->addToXsheet(fx.getPointer());

  return context()->thisObject();
}

QScriptValue Scene::setFrameRate(double fps) {
  if (fps <= 0) {
    return context()->throwError(tr("Frame rate must be positive"));
  }
  m_scene->getProperties()->getOutputProperties()->setFrameRate(fps);
  return context()->thisObject();
}

QScriptValue Scene::buildMesh(const QScriptValue &imageArg,
                              const QString &levelName) {
  Image *img = qscriptvalue_cast<Image *>(imageArg);
  if (!img || !img->getImg()) {
    return context()->throwError(tr("Expected an Image argument"));
  }

  // Extract raster from Raster or ToonzRaster image
  TRasterP ras;
  double dpix = 72.0, dpiy = 72.0;
  if (TRasterImageP ri = img->getImg()) {
    ras = ri->getRaster();
    ri->getDpi(dpix, dpiy);
  } else if (TToonzImageP ti = img->getImg()) {
    ras = ti->getRaster();
    ti->getDpi(dpix, dpiy);
  } else {
    return context()->throwError(
        tr("buildMesh requires a Raster or ToonzRaster image"));
  }
  if (!ras) {
    return context()->throwError(tr("Image has no raster data"));
  }
  if (dpix <= 0) dpix = 72.0;
  if (dpiy <= 0) dpiy = 72.0;

  if (levelName.isEmpty()) {
    return context()->throwError(tr("Level name cannot be empty"));
  }
  if (m_scene->getLevelSet()->hasLevel(levelName.toStdWString())) {
    return context()->throwError(
        tr("Level name '%1' is already used").arg(levelName));
  }

  // Build mesh from raster
  MeshBuilderOptions opts;
  opts.m_margin               = 5;
  opts.m_targetEdgeLength     = 15.0;
  opts.m_targetMaxVerticesCount = 0;
  opts.m_transparentColor     = TPixel64::Transparent;

  TMeshImageP meshImg = ::buildMesh(ras, opts);
  if (!meshImg || meshImg->meshes().empty()) {
    return context()->throwError(tr("Failed to build mesh from image"));
  }

  // Center the mesh: buildMesh returns coords with origin at lower-left of
  // the raster, but OpenToonz expects images centered at the origin.
  int w = ras->getLx(), h = ras->getLy();
  transform(meshImg, TTranslation(-w * 0.5, -h * 0.5));

  // Create mesh level
  TXshLevel *xl =
      m_scene->createNewLevel(MESH_XSHLEVEL, levelName.toStdWString());
  TXshSimpleLevel *sl = xl->getSimpleLevel();
  if (!sl) {
    return context()->throwError(tr("Failed to create mesh level"));
  }

  // Set DPI to match source image
  LevelProperties *lprop = sl->getProperties();
  lprop->setDpiPolicy(LevelProperties::DP_CustomDpi);
  lprop->setDpi(TPointD(dpix, dpiy));

  // Store mesh as frame 1
  sl->setFrame(TFrameId(1), meshImg.getPointer());
  sl->setDirtyFlag(true);

  return create(engine(), new Level(sl));
}

QScriptValue Scene::createSpline(const QScriptValue &pointArray) {
  if (!pointArray.isArray()) {
    return context()->throwError(tr("Expected an array of [x, y] points"));
  }

  quint32 len = pointArray.property("length").toUInt32();
  if (len < 3) {
    return context()->throwError(
        tr("Spline needs at least 3 control points"));
  }

  std::vector<TPointD> points;
  for (quint32 i = 0; i < len; i++) {
    QScriptValue pt = pointArray.property(i);
    if (!pt.isArray() || pt.property("length").toUInt32() < 2) {
      return context()->throwError(
          tr("Each point must be [x, y], got %1").arg(pt.toString()));
    }
    double x = pt.property(0).toNumber();
    double y = pt.property(1).toNumber();
    points.push_back(TPointD(x, y));
  }

  TStroke *stroke                   = new TStroke(points);
  TStageObjectSpline *spline        = new TStageObjectSpline();
  spline->setStroke(stroke);

  TStageObjectTree *tree = m_scene->getXsheet()->getStageObjectTree();
  tree->assignUniqueSplineId(spline);
  tree->insertSpline(spline);

  // Return the spline index
  int idx = tree->getSplineCount() - 1;
  return QScriptValue(idx);
}

QScriptValue Scene::setCameraSize(int w, int h) {
  if (w <= 0 || h <= 0) {
    return context()->throwError(
        tr("Camera width and height must be positive"));
  }
  TCamera *camera = m_scene->getCurrentCamera();
  camera->setRes(TDimension(w, h));
  // Set size in inches to maintain square pixels (at 72 dpi stage convention)
  camera->setSize(TDimensionD((double)w / 72.0, (double)h / 72.0));
  return context()->thisObject();
}

QScriptValue Scene::getCameraSize() {
  TCamera *camera    = m_scene->getCurrentCamera();
  TDimension res     = camera->getRes();
  QScriptValue result = engine()->newObject();
  result.setProperty("width", res.lx);
  result.setProperty("height", res.ly);
  return result;
}

}  // namespace TScriptBinding
