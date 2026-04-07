package main

import (
	"fmt"
	"log"
	"os"
	"time"

	"github.com/joho/godotenv"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"go-event-orders/internal/domain/orders"
)

// InitDB initializes and returns a GORM database connection
func InitDB() (*gorm.DB, error) {
	// Load environment variables from .env file
	if err := godotenv.Load(".env"); err != nil {
		log.Printf("Warning: Error loading .env file: %v", err)
	}
	folder := "logs"
	os.MkdirAll(folder, os.ModePerm)
	logFileName := fmt.Sprintf("logs/schema_migration_%s.log", time.Now().Format("20060102150405"))
	gormLogFile, err := os.OpenFile(logFileName, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o666)
	if err != nil {
		return nil, fmt.Errorf("failed to open gorm.log file: %w", err)
	}
	gormLogger := logger.New(
		log.New(gormLogFile, "\r\n", log.LstdFlags), // io.Writer
		logger.Config{
			LogLevel:                  logger.Info, // Change to desired level
			IgnoreRecordNotFoundError: true,
			Colorful:                  false,
		},
	)
	log.Printf("Initializing database connection to: %s", os.Getenv("DB_HOST"))
	dsn := fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=disable TimeZone=UTC",
		os.Getenv("DB_HOST"),
		os.Getenv("DB_USER"),
		os.Getenv("DB_PASSWORD"),
		os.Getenv("DB_NAME"),
		os.Getenv("DB_PORT"),
	)
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: gormLogger, // Use custom logger
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}
	fmt.Println("Database connection successful.")
	return db, nil
}

func main() {
	log.Println("Starting database schema migration...")
	// Connect to the database
	db, err := InitDB()
	if err != nil {
		log.Fatalf("FATAL: Could not connect to database: %v", err)
	}

	err = db.Transaction(func(tx *gorm.DB) error {
		log.Printf("  -> Migrating models...")
		return tx.AutoMigrate(
			&orders.Client{},
			&orders.Product{},
			&orders.Order{},
			&orders.OrderItem{},
		)
	})

	if err != nil {
		log.Printf("  -> ❌ FAILED to migrate models: %v", err)
	} else {
		log.Printf("  -> ✅ Successfully migrated models")
	}

	log.Println("🎉 Schema migration process finished.")
}
