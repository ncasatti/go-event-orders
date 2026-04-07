package main

import (
	"context"
	"encoding/json"
	"fmt"
	"go-event-orders/internal/dto/request"
	"go-event-orders/internal/dto/response"
	"go-event-orders/internal/infrastructure/storage"
	"go-event-orders/internal/shared"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
)

var s3Client *storage.S3Client

func init() {
	var err error
	bucketName := shared.GetEnv("ORDERS_BUCKET_NAME", "orders")
	s3Client, err = storage.NewS3Client(bucketName)
	if err != nil {
		panic(fmt.Sprintf("Failed to initialize S3 client: %v", err))
	}
}

// HandleRequest handles the POST request to submit orders
func HandleRequest(ctx context.Context, req events.APIGatewayV2HTTPRequest) (events.APIGatewayProxyResponse, error) {
	// Parse request body
	var payload request.OrderPayload
	if err := json.Unmarshal([]byte(req.Body), &payload); err != nil {
		return response.ApiError(400, "Invalid JSON payload: "+err.Error())
	}

	if len(payload.Orders) == 0 {
		return response.ApiError(400, "No orders provided")
	}

	// Upload to S3
	timestamp := time.Now().Format("20060102150405")
	s3Key := fmt.Sprintf("orders/%s-%s.json", timestamp, payload.DeviceID)

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return response.ApiError(500, "Failed to marshal payload")
	}

	err = s3Client.Upload(ctx, s3Key, jsonData, map[string]string{"device_id": payload.DeviceID})

	if err != nil {
		return response.ApiError(500, "Failed to upload order to processing queue: "+err.Error())
	}

	return response.ApiSuccess(map[string]string{
		"message": "Orders received and queued for processing",
		"key":     s3Key,
	})
}

func main() {
	lambda.Start(HandleRequest)
}
