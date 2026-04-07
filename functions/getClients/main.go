package main

import (
	"context"
	"go-event-orders/internal/domain/orders"
	"go-event-orders/internal/dto/response"
	"go-event-orders/internal/infrastructure/database"
	"go-event-orders/internal/infrastructure/observability"

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

// HandleRequest handles the Lambda request to get clients
func HandleRequest(ctx context.Context, request events.APIGatewayV2HTTPRequest) (events.APIGatewayProxyResponse, error) {

	if db == nil {
		return response.ApiError(500, "Error connecting to database")
	}

	var clients []orders.Client
	// Query all active clients
	if err := db.Where("is_active = ?", true).Find(&clients).Error; err != nil {
		return response.ApiError(500, "Error fetching clients: "+err.Error())
	}

	return response.ApiSuccess(clients)
}

func main() {
	lambda.Start(HandleRequest)
}
