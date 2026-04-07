package database

import (
	"fmt"
	"os"
	"time"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

var (
	// Singleton DB instance
	dbClient *gorm.DB
)

// GetDB returns the singleton DB connection, initializing it if necessary
func GetDB() (*gorm.DB, error) {
	if dbClient != nil {
		return dbClient, nil
	}

	return InitDB()
}

// InitDB initializes the database connection using environment variables
func InitDB() (*gorm.DB, error) {
	dbHost := os.Getenv("DB_HOST")
	dbUser := os.Getenv("DB_USER")
	dbPassword := os.Getenv("DB_PASSWORD")
	dbName := os.Getenv("DB_NAME")
	dbPort := os.Getenv("DB_PORT")

	if dbHost == "" {
		// Provide defaults or fail, but better to log missing config
		fmt.Println("WARNING: DB_HOST not set")
	}

	dsn := fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=disable",
		dbHost, dbUser, dbPassword, dbName, dbPort)

	var err error
	start := time.Now()
	// Open connection
	dbClient, err = gorm.Open(postgres.Open(dsn), &gorm.Config{})
	duration := time.Since(start)

	if err != nil {
		fmt.Printf("Database connection failed after %v: %v\n", duration, err)
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	fmt.Printf("Database connection successful in %v\n", duration)
	return dbClient, nil
}

// CheckDBConnection tests the connection
func CheckDBConnection(db *gorm.DB) error {
	sqlDB, err := db.DB()
	if err != nil {
		return err
	}
	return sqlDB.Ping()
}

// WithSchema sets the search path (tenancy)
func WithSchema(db *gorm.DB, schemaName string, fc func(tx *gorm.DB) error) error {
	return db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Exec(fmt.Sprintf("SET search_path TO %s", schemaName)).Error; err != nil {
			return err
		}
		return fc(tx)
	})
}
