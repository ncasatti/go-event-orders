package main

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"go-event-orders/internal/domain/orders"
	"go-event-orders/internal/dto/request"
	"go-event-orders/internal/infrastructure/database"
	"go-event-orders/internal/infrastructure/storage"
	"go-event-orders/internal/repository"
	"go-event-orders/internal/shared"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
)

var (
	s3Client *storage.S3Client
)

func init() {
	var err error
	s3Client, err = storage.NewS3Client("") // bucket name viene en el evento
	if err != nil {
		panic(fmt.Sprintf("Failed to initialize S3 client: %v", err))
	}
}

// HandleSQSEvent processes SQS messages containing S3 events
func HandleSQSEvent(ctx context.Context, sqsEvent events.SQSEvent) (events.SQSEventResponse, error) {

	failures := events.SQSEventResponse{
		BatchItemFailures: []events.SQSBatchItemFailure{},
	}

	for _, record := range sqsEvent.Records {
		var s3Event events.S3Event
		if err := json.Unmarshal([]byte(record.Body), &s3Event); err != nil {
			shared.LogError("Failed to parse S3 event from SQS", err)
			failures.BatchItemFailures = append(failures.BatchItemFailures, events.SQSBatchItemFailure{ItemIdentifier: record.MessageId})
			continue
		}

		for _, s3Record := range s3Event.Records {
			bucket := s3Record.S3.Bucket.Name
			key := s3Record.S3.Object.Key

			shared.LogInfo(fmt.Sprintf("Processing file: %s from bucket: %s", key, bucket))

			if err := processOrderFile(ctx, bucket, key); err != nil {
				shared.LogError("Failed to process order file", err)
				failures.BatchItemFailures = append(failures.BatchItemFailures, events.SQSBatchItemFailure{ItemIdentifier: record.MessageId})
			}
		}
	}
	return failures, nil
}

func processOrderFile(ctx context.Context, bucket, key string) error {
	// 1. Download
	body, err := s3Client.Download(ctx, bucket, key)
	if err != nil {
		return fmt.Errorf("S3 GetObject failed: %w", err)
	}

	var payload request.OrderPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		return fmt.Errorf("failed to parse OrderPayload: %w", err)
	}

	// 2. Connect DB
	db, err := database.GetDB()
	if err != nil {
		return fmt.Errorf("failed to connect to DB: %w", err)
	}

	// 3. Validate
	validationRepo := repository.NewValidationRepository(db)
	clientRepo := repository.NewClientRepositoryAdapter(validationRepo)
	productRepo := repository.NewProductRepositoryAdapter(validationRepo)
	validator := orders.NewOrderValidator(clientRepo, productRepo)

	validationRes := orders.NewValidationResult()
	for i, order := range payload.Orders {
		orderResult := validator.ValidateOrder(ctx, &order)
		if orderResult.HasErrors() {
			for _, err := range orderResult.Errors {
				validationRes.AddError(fmt.Sprintf("order[%d]: %s", i, err))
			}
		}
	}

	if validationRes.HasErrors() {
		shared.LogInfo(fmt.Sprintf("Validation failed for %s: %v", key, validationRes.Errors))
		// Here we might want to move the file to a DLQ bucket or log error logic.
		// For now, returning error to trigger SQS retry/DLQ mechanism.
		return fmt.Errorf("validation failed: %v", validationRes.Errors)
	}

	// 4. Insert
	start := time.Now()
	ordersRepo := repository.NewOrdersRepository(db)
	if err := ordersRepo.InsertOrderPayload(payload.DeviceID, payload.Orders); err != nil {
		return fmt.Errorf("insertion failed: %w", err)
	}

	shared.LogInfo(fmt.Sprintf("Successfully processed order %s in %d ms", key, time.Since(start).Milliseconds()))

	return nil
}

func main() {
	lambda.Start(HandleSQSEvent)
}
