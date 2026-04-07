package main

import (
	"context"
	"fmt"
	"go-event-orders/internal/dto/response"
	"go-event-orders/internal/infrastructure/database"
	"go-event-orders/internal/infrastructure/observability"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"gorm.io/gorm"
)

var db *gorm.DB

func init() {
	var err error
	db, err = database.GetDB()
	if err != nil {
		observability.LogErrorCtx("Error connecting to database", err, map[string]any{
			"event": "init_db_connection",
		})
	}
}

func HandleRequest(ctx context.Context, request events.APIGatewayV2HTTPRequest) (events.APIGatewayProxyResponse, error) {
	fmt.Println("Iniciando función status")

	databaseStatus := "connected"
	if db == nil {
		databaseStatus = "disconnected"
	}

	apiStatus := map[string]any{
		"status":    "ok",
		"message":   "API is running",
		"version":   "1.0.0",
		"db_status": databaseStatus,
		"timestamp": time.Now().Format("2006-01-02 15:04:05"),
	}

	return response.ApiResponse(200, "success", map[string]any{"api_status": apiStatus}, "")
}

func main() {
	lambda.Start(HandleRequest)
}
