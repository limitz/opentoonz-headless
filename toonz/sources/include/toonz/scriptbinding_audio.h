#pragma once
#ifndef SCRIPTBINDING_AUDIO_H
#define SCRIPTBINDING_AUDIO_H

#include "toonz/scriptbinding.h"

namespace TScriptBinding {

class DVAPI Audio final : public Wrapper {
  Q_OBJECT

public:
  Audio();
  ~Audio();

  WRAPPER_STD_METHODS(Audio)
  Q_INVOKABLE QScriptValue toString();

  // Load a sound file into a scene on a new sound column.
  // Returns the column index.
  Q_INVOKABLE QScriptValue loadAudio(const QScriptValue &sceneArg,
                                     const QString &path, int startFrame);

  // Save the audio from a sound column to a WAV file.
  Q_INVOKABLE QScriptValue saveAudio(const QScriptValue &sceneArg, int col,
                                     const QString &path);

  // Apply lip sync data (text file: "frame phoneme\n..." pairs)
  // to an XSheet column, mapping phoneme codes to frame IDs in a mouth level.
  Q_INVOKABLE QScriptValue applyLipSync(const QScriptValue &sceneArg,
                                        int targetCol,
                                        const QScriptValue &mouthLevelArg,
                                        const QScriptValue &phonemeMapArg,
                                        const QString &dataPath,
                                        int startFrame);

  // Get sound column duration in frames
  Q_INVOKABLE QScriptValue getAudioDuration(const QScriptValue &sceneArg,
                                            int col);
};

}  // namespace TScriptBinding

Q_DECLARE_METATYPE(TScriptBinding::Audio *)

#endif
