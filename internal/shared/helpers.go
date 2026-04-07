package shared

import (
	"fmt"
	"os"
)

// GetEnv gets an environment variable with a fallback default value
func GetEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

// LogInfo logs informational messages
func LogInfo(message string) {
	fmt.Printf("[INFO] %s\n", message)
}

// LogError logs error messages
func LogError(message string, err error) {
	if err != nil {
		fmt.Printf("[ERROR] %s: %v\n", message, err)
	} else {
		fmt.Printf("[ERROR] %s\n", message)
	}
}
