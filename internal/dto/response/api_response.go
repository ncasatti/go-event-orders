package response

import (
	"encoding/json"

	"github.com/aws/aws-lambda-go/events"
)

type JSendResponse struct {
	Status  string `json:"status"`
	Data    any    `json:"data,omitempty"`
	Message string `json:"message,omitempty"`
}

// ApiResponse formats a standard JSend response
func ApiResponse(statusCode int, status string, data interface{}, message string) (events.APIGatewayProxyResponse, error) {
	payload := JSendResponse{
		Status:  status,
		Data:    data,
		Message: message,
	}
	body, _ := json.Marshal(payload)
	return events.APIGatewayProxyResponse{
		StatusCode: statusCode,
		Headers:    map[string]string{"Content-Type": "application/json"},
		Body:       string(body),
	}, nil
}

// ApiSuccess shortcut for success response
func ApiSuccess(data interface{}) (events.APIGatewayProxyResponse, error) {
	return ApiResponse(200, "success", data, "")
}

// ApiError shortcut for error response
func ApiError(statusCode int, message string) (events.APIGatewayProxyResponse, error) {
	return ApiResponse(statusCode, "error", nil, message)
}
