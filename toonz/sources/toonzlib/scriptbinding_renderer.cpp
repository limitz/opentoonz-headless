

#include "toonz/scriptbinding_renderer.h"
#include "toonz/scriptbinding_scene.h"
#include "toonz/scriptbinding_level.h"
#include "toonz/txsheet.h"
#include "toonz/txshsimplelevel.h"

#include "toonz/toonzscene.h"
#include "trenderer.h"
#include "toonz/scenefx.h"
#include "toonz/sceneproperties.h"
#include "toonz/tcamera.h"
#include "toutputproperties.h"
#include <QMutex>
#include <QMutexLocker>
#include <QWaitCondition>
#include <QThread>

#include "timagecache.h"

namespace TScriptBinding {

//=======================================================

static QScriptValue getScene(QScriptContext *context,
                             const QScriptValue &sceneArg, Scene *&scene) {
  scene = qscriptvalue_cast<Scene *>(sceneArg);
  if (!scene)
    return context->throwError(
        QObject::tr("First argument must be a scene : %1")
            .arg(sceneArg.toString()));
  if (scene->getToonzScene() == 0)
    return context->throwError(QObject::tr("Can't render empty scene"));
  return QScriptValue();
}

static void valueToIntList(const QScriptValue &arr, QList<int> &list) {
  list.clear();
  if (arr.isArray()) {
    int length = arr.property("length").toInteger();
    for (int i = 0; i < length; i++) list.append(arr.property(i).toInteger());
  }
}

//=======================================================

class Renderer::Imp final : public TRenderPort {
public:
  TPointD m_cameraDpi;

  QMutex m_mutex;
  QWaitCondition m_condition;
  bool m_completed;

  // Rendered results — written on the worker thread under m_mutex,
  // read on the main thread after m_completed is set.
  TImageP m_resultImage;
  QList<QPair<TFrameId, TImageP>> m_resultFrames;

  TRenderer m_renderer;

  QList<int> m_columnList;
  QList<int> m_frameList;

  Imp() : m_completed(false) {
    m_renderer.setThreadsCount(1);
    m_renderer.addPort(this);
  }

  ~Imp() {}

  void setRenderArea(ToonzScene *scene) {
    TDimension cameraRes = scene->getCurrentCamera()->getRes();
    double rx = cameraRes.lx * 0.5, ry = cameraRes.ly * 0.5;
    TRectD renderArea(-rx, -ry, rx, ry);
    TRenderPort::setRenderArea(renderArea);
    m_cameraDpi = scene->getCurrentCamera()->getDpi();
  }

  void enableColumns(ToonzScene *scene, QList<bool> &oldStatus) {
    if (m_columnList.empty()) return;
    QList<bool> newStatus;
    TXsheet *xsh = scene->getXsheet();
    for (int i = 0; i < xsh->getColumnCount(); i++) {
      oldStatus.append(xsh->getColumn(i)->isPreviewVisible());
      newStatus.append(false);
    }
    for (int i : m_columnList) {
      if (0 <= i && i < xsh->getColumnCount()) newStatus[i] = true;
    }
    for (int i = 0; i < newStatus.length(); i++) {
      xsh->getColumn(i)->setPreviewVisible(newStatus[i]);
    }
  }

  void restoreColumns(ToonzScene *scene, const QList<bool> &oldStatus) {
    TXsheet *xsh = scene->getXsheet();
    for (int i = 0; i < oldStatus.length(); i++) {
      xsh->getColumn(i)->setPreviewVisible(oldStatus[i]);
    }
  }

  std::vector<TRenderer::RenderData> *makeRenderData(
      ToonzScene *scene, const std::vector<int> &rows) {
    TRenderSettings settings =
        scene->getProperties()->getOutputProperties()->getRenderSettings();

    QList<bool> oldColumnStates;
    enableColumns(scene, oldColumnStates);

    std::vector<TRenderer::RenderData> *rds =
        new std::vector<TRenderer::RenderData>;
    for (int i = 0; i < (int)rows.size(); i++) {
      double frame = rows[i];
      TFxP sceneFx = buildSceneFx(scene, frame, 1, false);
      TFxPair fxPair;
      fxPair.m_frameA = sceneFx;
      rds->push_back(TRenderer::RenderData(frame, settings, fxPair));
    }

    restoreColumns(scene, oldColumnStates);
    return rds;
  }

  void render(std::vector<TRenderer::RenderData> *rds) {
    {
      QMutexLocker locker(&m_mutex);
      m_completed   = false;
      m_resultImage = TImageP();
      m_resultFrames.clear();
    }

    m_renderer.startRendering(rds);

    // Wait for the worker thread to signal completion.
    QMutexLocker locker(&m_mutex);
    while (!m_completed) {
      m_condition.wait(&m_mutex, 30000);  // 30s timeout
      break;  // either signaled or timed out
    }
  }

  TImageP renderFrame(ToonzScene *scene, int row) {
    setRenderArea(scene);
    std::vector<int> rows;
    rows.push_back(row);
    render(makeRenderData(scene, rows));

    QMutexLocker locker(&m_mutex);
    return m_resultImage;
  }

  void renderScene(ToonzScene *scene, Level *outputLevel) {
    setRenderArea(scene);
    std::vector<int> rows;
    if (m_frameList.empty()) {
      for (int i = 0; i < scene->getFrameCount(); i++) rows.push_back(i);
    } else {
      for (int i = 0; i < m_frameList.length(); i++)
        rows.push_back(m_frameList[i]);
    }
    render(makeRenderData(scene, rows));

    QMutexLocker locker(&m_mutex);
    for (const auto &pair : m_resultFrames)
      outputLevel->setFrame(pair.first, pair.second);
  }

  // --- TRenderPort callbacks (called on the worker thread) ---

  void onRenderRasterStarted(const RenderData &renderData) override {}

  void onRenderRasterCompleted(const RenderData &renderData) override {
    TRasterP outputRaster = renderData.m_rasA;
    TRasterImageP img(outputRaster->clone());
    img->setDpi(m_cameraDpi.x, m_cameraDpi.y);

    QMutexLocker locker(&m_mutex);
    m_resultImage = img;
    for (int i = 0; i < (int)renderData.m_frames.size(); i++) {
      TFrameId fid((int)(renderData.m_frames[i]) + 1);
      m_resultFrames.append(qMakePair(fid, TImageP(img)));
    }
  }

  void onRenderFailure(const RenderData &renderData,
                        TException &e) override {}

  void onRenderFinished(bool isCanceled = false) override {
    QMutexLocker locker(&m_mutex);
    m_completed = true;
    m_condition.wakeAll();
  }
};

//=======================================================

Renderer::Renderer() : m_imp(new Imp()) {}

Renderer::~Renderer() {}

QScriptValue Renderer::ctor(QScriptContext *context, QScriptEngine *engine) {
  QScriptValue r = create(engine, new Renderer());
  r.setProperty("frames", engine->newArray());
  r.setProperty("columns", engine->newArray());
  return r;
}

QScriptValue Renderer::toString() { return "Renderer"; }

QScriptValue Renderer::renderScene(const QScriptValue &sceneArg) {
  QScriptValue obj = context()->thisObject();
  valueToIntList(obj.property("frames"), m_imp->m_frameList);
  valueToIntList(obj.property("columns"), m_imp->m_columnList);

  Scene *scene     = 0;
  QScriptValue err = getScene(context(), sceneArg, scene);
  if (err.isError()) return err;

  Level *outputLevel = new Level();
  m_imp->renderScene(scene->getToonzScene(), outputLevel);
  return create(engine(), outputLevel);
}

Q_INVOKABLE QScriptValue Renderer::renderFrame(const QScriptValue &sceneArg,
                                               int frame) {
  QScriptValue obj = context()->thisObject();
  valueToIntList(obj.property("columns"), m_imp->m_columnList);

  Scene *scene     = 0;
  QScriptValue err = getScene(context(), sceneArg, scene);
  if (err.isError()) return err;

  TImageP img = m_imp->renderFrame(scene->getToonzScene(), frame);

  Image *outputImage = new Image();
  if (img) outputImage->setImg(img);
  return create(engine(), outputImage);
}

void Renderer::dumpCache() {}

}  // namespace TScriptBinding
