package observability

import (
	"os"

	log "github.com/sirupsen/logrus"
)

func init() {
	// Configurar Logrus para formato JSON
	log.SetFormatter(&log.JSONFormatter{
		TimestampFormat: "2006-01-02T15:04:05.000Z07:00",
		FieldMap: log.FieldMap{
			log.FieldKeyTime:  "timestamp",
			log.FieldKeyLevel: "level",
			log.FieldKeyMsg:   "message",
		},
	})

	// Output a stdout (CloudWatch captura stdout automáticamente)
	log.SetOutput(os.Stdout)

	// Nivel de log (INFO por default, puede configurarse via env var)
	logLevel := os.Getenv("LOG_LEVEL")
	switch logLevel {
	case "DEBUG":
		log.SetLevel(log.DebugLevel)
	case "WARN":
		log.SetLevel(log.WarnLevel)
	case "ERROR":
		log.SetLevel(log.ErrorLevel)
	default:
		log.SetLevel(log.InfoLevel)
	}
}

// LogInfoCtx logs informational messages with structured context
// Ejemplo: LogInfoCtx("processing_started", map[string]any{"vendor_id": "XSI001", "schema": "xionico"})
func LogInfoCtx(message string, context map[string]any) {
	if context == nil {
		context = make(map[string]any)
	}
	log.WithFields(log.Fields(context)).Info(message)
}

// LogErrorCtx logs error messages with structured context
// Ejemplo: LogErrorCtx("processing_failed", err, map[string]any{"s3_key": key})
func LogErrorCtx(message string, err error, context map[string]any) {
	if context == nil {
		context = make(map[string]any)
	}
	if err != nil {
		context["error"] = err.Error()
	}
	log.WithFields(log.Fields(context)).Error(message)
}

// LogWarnCtx logs warning messages with structured context
func LogWarnCtx(message string, context map[string]any) {
	if context == nil {
		context = make(map[string]any)
	}
	log.WithFields(log.Fields(context)).Warn(message)
}

// LogDebugCtx logs debug messages with structured context
func LogDebugCtx(message string, context map[string]any) {
	if context == nil {
		context = make(map[string]any)
	}
	log.WithFields(log.Fields(context)).Debug(message)
}

// LogLambdaDuration logs the duration of a lambda function execution
func LogLambdaDuration(functionName string, durationMs int64, status string, schema string) {
	context := map[string]any{
		"schema":      schema,
		"function":    functionName,
		"duration_ms": durationMs,
		"status":      status,
	}
	log.WithFields(log.Fields(context)).Info("lambda_duration")
}
