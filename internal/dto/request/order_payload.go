package request

import "go-event-orders/internal/domain/orders"

// OrderPayload represents the incoming data from the client
type OrderPayload struct {
	DeviceID string         `json:"device_id"`
	Orders   []orders.Order `json:"orders"`
}
