
#include <QGuiApplication>
#include <QTextStream>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QTimer>

#include "tsystem.h"
#include "tthread.h"
#include "tenv.h"
#include "tiio_std.h"
#include "tnzimage.h"
#include "toonz/scriptengine.h"

// FX init functions (from tnzstdfx and colorfx libraries)
void initStdFx();
void initColorFx();

//=========================================================
// JSON-RPC handler that wraps ScriptEngine
//=========================================================

class JsonRpcHandler : public QObject {
  Q_OBJECT

  ScriptEngine *m_scriptEngine;
  QTextStream m_stdin;
  QTextStream m_stdout;
  int m_currentId;
  QString m_pendingOutput;

public:
  JsonRpcHandler(QObject *parent = nullptr)
      : QObject(parent)
      , m_scriptEngine(new ScriptEngine())
      , m_stdin(stdin, QIODevice::ReadOnly)
      , m_stdout(stdout, QIODevice::WriteOnly)
      , m_currentId(-1) {
    connect(m_scriptEngine, &ScriptEngine::evaluationDone, this,
            &JsonRpcHandler::onEvaluationDone);

    connect(m_scriptEngine,
            static_cast<void (ScriptEngine::*)(int, const QString &)>(
                &ScriptEngine::output),
            this, &JsonRpcHandler::onOutput);
  }

  ~JsonRpcHandler() { delete m_scriptEngine; }

public slots:
  void processNextLine() {
    if (m_stdin.atEnd()) {
      QCoreApplication::quit();
      return;
    }

    QString line = m_stdin.readLine();
    if (line.isEmpty()) {
      QTimer::singleShot(0, this, &JsonRpcHandler::processNextLine);
      return;
    }

    QJsonParseError parseError;
    QJsonDocument doc = QJsonDocument::fromJson(line.toUtf8(), &parseError);

    if (parseError.error != QJsonParseError::NoError) {
      sendError(-1, -32700, "Parse error: " + parseError.errorString());
      QTimer::singleShot(0, this, &JsonRpcHandler::processNextLine);
      return;
    }

    QJsonObject req = doc.object();
    m_currentId     = req.value("id").toInt(-1);
    QString method  = req.value("method").toString();
    QJsonObject params = req.value("params").toObject();

    if (method == "eval") {
      QString code = params.value("code").toString();
      if (code.isEmpty()) {
        sendError(m_currentId, -32602, "Missing 'code' parameter");
        QTimer::singleShot(0, this, &JsonRpcHandler::processNextLine);
        return;
      }
      m_pendingOutput.clear();
      m_scriptEngine->evaluate(code);
      // Wait for evaluationDone signal
    } else if (method == "ping") {
      sendResult(m_currentId, QJsonValue("pong"));
      QTimer::singleShot(0, this, &JsonRpcHandler::processNextLine);
    } else if (method == "quit") {
      sendResult(m_currentId, QJsonValue("bye"));
      QCoreApplication::quit();
    } else {
      sendError(m_currentId, -32601, "Unknown method: " + method);
      QTimer::singleShot(0, this, &JsonRpcHandler::processNextLine);
    }
  }

private slots:
  void onOutput(int type, const QString &value) {
    // Accumulate output from print/warning calls during evaluation
    if (!m_pendingOutput.isEmpty()) m_pendingOutput += "\n";
    m_pendingOutput += value;
  }

  void onEvaluationDone() {
    // The ScriptEngine emits output signals before evaluationDone
    // Build the response from accumulated output
    QJsonObject result;
    if (!m_pendingOutput.isEmpty()) {
      result["output"] = m_pendingOutput;
    }
    result["ok"] = true;

    sendResult(m_currentId, result);
    QTimer::singleShot(0, this, &JsonRpcHandler::processNextLine);
  }

private:
  void sendResult(int id, const QJsonValue &result) {
    QJsonObject response;
    response["jsonrpc"] = "2.0";
    response["id"]      = id;
    response["result"]  = result;
    writeLine(response);
  }

  void sendError(int id, int code, const QString &message) {
    QJsonObject error;
    error["code"]    = code;
    error["message"] = message;

    QJsonObject response;
    response["jsonrpc"] = "2.0";
    response["id"]      = id;
    response["error"]   = error;
    writeLine(response);
  }

  void writeLine(const QJsonObject &obj) {
    QJsonDocument doc(obj);
    m_stdout << doc.toJson(QJsonDocument::Compact) << "\n";
    m_stdout.flush();
  }
};

//=========================================================
// Main
//=========================================================

static const char *rootVarName    = "TOONZROOT";
static const char *systemVarPrefix = "TOONZ";

int main(int argc, char *argv[]) {
  QGuiApplication app(argc, argv);

  QCoreApplication::setOrganizationName("OpenToonz");
  QCoreApplication::setOrganizationDomain("opentoonz.github.io");
  QCoreApplication::setApplicationName("toonz_headless");

  // Core initialization (following tconverter pattern)
  TEnv::setRootVarName(rootVarName);
  TEnv::setSystemVarPrefix(systemVarPrefix);
  TEnv::setApplicationFileName(argv[0]);

  TThread::init();
  TSystem::hasMainLoop(true);  // Need event loop for ScriptEngine signals

  Tiio::defineStd();
  initImageIo();
  initStdFx();
  initColorFx();

  // Print ready message
  QTextStream out(stdout);
  QJsonObject ready;
  ready["jsonrpc"] = "2.0";
  ready["method"]  = "ready";
  ready["params"]  = QJsonObject{{"version", "1.0"}};
  out << QJsonDocument(ready).toJson(QJsonDocument::Compact) << "\n";
  out.flush();

  // Start processing
  JsonRpcHandler handler;
  QTimer::singleShot(0, &handler, &JsonRpcHandler::processNextLine);

  return app.exec();
}

#include "main.moc"
