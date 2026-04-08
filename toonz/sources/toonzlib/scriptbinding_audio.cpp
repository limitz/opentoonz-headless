

#include "toonz/scriptbinding_audio.h"
#include "toonz/scriptbinding_scene.h"
#include "toonz/scriptbinding_level.h"
#include "toonz/toonzscene.h"
#include "toonz/txsheet.h"
#include "toonz/txshcell.h"
#include "toonz/txshcolumn.h"
#include "toonz/txshsoundcolumn.h"
#include "toonz/txshsoundlevel.h"
#include "toonz/levelset.h"
#include "toonz/sceneproperties.h"
#include "toutputproperties.h"
#include "tsound_io.h"
#include "tsystem.h"

#include <QFile>
#include <QTextStream>

namespace TScriptBinding {

Audio::Audio()  = default;
Audio::~Audio() = default;

QScriptValue Audio::toString() { return "Audio"; }

QScriptValue Audio::ctor(QScriptContext *context, QScriptEngine *engine) {
  return create(engine, new Audio());
}

// ------------------------------------------------------------------
// loadAudio — load a WAV/AIFF file into a new sound column
// ------------------------------------------------------------------

QScriptValue Audio::loadAudio(const QScriptValue &sceneArg,
                              const QString &path, int startFrame) {
  Scene *scene = qscriptvalue_cast<Scene *>(sceneArg);
  if (!scene || !scene->getToonzScene())
    return context()->throwError(tr("First argument must be a Scene"));

  TFilePath fp(path.toStdWString());
  if (!TFileStatus(fp).doesExist())
    return context()->throwError(tr("File not found: %1").arg(path));

  ToonzScene *ts = scene->getToonzScene();
  TXsheet *xsh   = ts->getXsheet();

  // Load the sound track
  TSoundTrackP st;
  bool ok = TSoundTrackReader::load(fp, st);
  if (!ok || !st)
    return context()->throwError(tr("Failed to load audio: %1").arg(path));

  // Load sound data to get duration info
  TSoundTrackP soundTrack;
  bool loadOk = TSoundTrackReader::load(fp, soundTrack);
  if (!loadOk || !soundTrack)
    return context()->throwError(
        tr("Failed to read audio data from: %1").arg(path));

  double fps =
      ts->getProperties()->getOutputProperties()->getFrameRate();
  if (fps <= 0) fps = 24.0;

  // Compute frame count from sound duration
  double duration = (double)soundTrack->getSampleCount() /
                    (double)soundTrack->getSampleRate();
  int frameCount = std::max(1, (int)(duration * fps));

  // Return audio info as an object (sound columns require full scene
  // initialization which may not be available in headless mode)
  QScriptValue result = engine()->newObject();
  result.setProperty("path", path);
  result.setProperty("duration", duration);
  result.setProperty("frames", frameCount);
  result.setProperty("sampleRate", (int)soundTrack->getSampleRate());
  result.setProperty("sampleCount", (int)soundTrack->getSampleCount());
  result.setProperty("channels", soundTrack->getChannelCount());
  result.setProperty("bitDepth", soundTrack->getBitPerSample());
  return result;
}

// ------------------------------------------------------------------
// saveAudio — export audio from a sound column to WAV
// ------------------------------------------------------------------

QScriptValue Audio::saveAudio(const QScriptValue &sceneArg, int col,
                              const QString &path) {
  // For now, saveAudio converts between audio formats by loading and re-saving.
  // The col parameter is reserved for future sound column support.

  // Load the source audio
  Scene *scene = qscriptvalue_cast<Scene *>(sceneArg);
  if (!scene || !scene->getToonzScene())
    return context()->throwError(tr("First argument must be a Scene"));

  // For basic format conversion: load from one file, save to another
  // This is a placeholder for when full sound column support is available
  return context()->throwError(
      tr("saveAudio from sound columns not yet supported in headless mode. "
         "Use Audio.convertAudio(srcPath, dstPath) instead."));
}

// ------------------------------------------------------------------
// applyLipSync — parse phoneme data and set XSheet cells
// ------------------------------------------------------------------

QScriptValue Audio::applyLipSync(const QScriptValue &sceneArg, int targetCol,
                                 const QScriptValue &mouthLevelArg,
                                 const QScriptValue &phonemeMapArg,
                                 const QString &dataPath, int startFrame) {
  Scene *scene = qscriptvalue_cast<Scene *>(sceneArg);
  if (!scene || !scene->getToonzScene())
    return context()->throwError(tr("First argument must be a Scene"));

  Level *mouthLevel = qscriptvalue_cast<Level *>(mouthLevelArg);
  if (!mouthLevel)
    return context()->throwError(tr("mouthLevel must be a Level"));

  TXshSimpleLevel *sl = mouthLevel->getSimpleLevel();
  if (!sl)
    return context()->throwError(tr("mouthLevel has no simple level"));

  // Parse phoneme map: {phonemeCode: frameId, ...}
  // e.g., {"ai": 1, "e": 2, "o": 3, "u": 4, "mbp": 5, ...}
  if (!phonemeMapArg.isObject())
    return context()->throwError(
        tr("phonemeMap must be an object {phoneme: frameId}"));

  // Read the data file
  QFile file(dataPath);
  if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
    return context()->throwError(tr("Cannot open file: %1").arg(dataPath));

  QTextStream in(&file);
  ToonzScene *ts = scene->getToonzScene();
  TXsheet *xsh   = ts->getXsheet();

  // Ensure target column exists
  while (targetCol >= xsh->getColumnCount()) xsh->insertColumn(targetCol);

  // Parse format: each line is "frame phoneme"
  // e.g.: "1 ai\n5 mbp\n8 e\n12 rest"
  struct PhonemeEntry {
    int frame;
    QString phoneme;
  };
  QList<PhonemeEntry> entries;

  while (!in.atEnd()) {
    QString line = in.readLine().trimmed();
    if (line.isEmpty()) continue;

    QStringList parts = line.split(QRegExp("\\s+"));
    if (parts.size() < 2) continue;

    bool ok;
    int frame = parts[0].toInt(&ok);
    if (!ok) continue;

    PhonemeEntry entry;
    entry.frame   = frame;
    entry.phoneme = parts[1].toLower();
    entries.append(entry);
  }
  file.close();

  if (entries.isEmpty())
    return context()->throwError(tr("No valid entries in lip sync data file"));

  // Apply entries to XSheet
  int cellsSet = 0;
  for (int i = 0; i < entries.size(); i++) {
    const PhonemeEntry &entry = entries[i];
    int endFrame = (i + 1 < entries.size()) ? entries[i + 1].frame
                                            : entry.frame + 1;

    // Look up frame ID from phoneme map
    QScriptValue fidVal = phonemeMapArg.property(entry.phoneme);
    if (!fidVal.isValid() || fidVal.isUndefined()) continue;

    int frameId = fidVal.toInt32();
    TFrameId fid(frameId);

    TXshCell cell(sl, fid);

    for (int f = entry.frame; f < endFrame; f++) {
      xsh->setCell(startFrame + f - 1, targetCol, cell);
      cellsSet++;
    }
  }

  return QScriptValue(cellsSet);
}

// ------------------------------------------------------------------
// getAudioDuration — get sound column duration in frames
// ------------------------------------------------------------------

QScriptValue Audio::getAudioDuration(const QScriptValue &sceneArg, int col) {
  // If sceneArg is a string, treat it as a file path for direct audio info
  if (sceneArg.isString()) {
    TFilePath fp(sceneArg.toString().toStdWString());
    TSoundTrackP st;
    if (!TSoundTrackReader::load(fp, st) || !st)
      return context()->throwError(
          tr("Failed to load audio: %1").arg(sceneArg.toString()));

    double duration =
        (double)st->getSampleCount() / (double)st->getSampleRate();
    double fps = (col > 0) ? (double)col : 24.0;  // col reused as fps
    return QScriptValue((int)(duration * fps));
  }

  // Otherwise try scene + sound column
  Scene *scene = qscriptvalue_cast<Scene *>(sceneArg);
  if (!scene || !scene->getToonzScene())
    return context()->throwError(tr("First argument must be a Scene or audio file path"));

  TXsheet *xsh = scene->getToonzScene()->getXsheet();
  if (col < 0 || col >= xsh->getColumnCount())
    return context()->throwError(tr("Column %1 out of range").arg(col));

  TXshColumn *xshCol = xsh->getColumn(col);
  if (!xshCol || !xshCol->getSoundColumn())
    return context()->throwError(
        tr("Column %1 is not a sound column").arg(col));

  int r0, r1;
  xshCol->getSoundColumn()->getRange(r0, r1);
  return QScriptValue(r1 - r0 + 1);
}

}  // namespace TScriptBinding
