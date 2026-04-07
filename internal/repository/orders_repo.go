package repository

import (
	"fmt"
	"go-event-orders/internal/domain/orders"
	"go-event-orders/internal/infrastructure/observability"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type OrdersRepository struct {
	db *gorm.DB
}

// NewOrdersRepository creates a new OrdersRepository instance
func NewOrdersRepository(db *gorm.DB) *OrdersRepository {
	return &OrdersRepository{db: db}
}

// InsertOrderPayload processes the incoming order payload
func (r *OrdersRepository) InsertOrderPayload(deviceID string, orderList []orders.Order) error {
	return r.db.Transaction(func(tx *gorm.DB) error {
		observability.LogInfoCtx("Starting order payload insertion", map[string]any{
			"device_id":   deviceID,
			"order_count": len(orderList),
		})

		for _, order := range orderList {
			// Insert Order

			if err := tx.Clauses(clause.OnConflict{DoNothing: true}).Omit("Items").Create(&order).Error; err != nil {
				return fmt.Errorf("failed to insert order: %w", err)
			}

			// If we have items
			if len(order.Items) > 0 {
				for i := range order.Items {
					order.Items[i].OrderID = order.ID // Link to created order
				}
				if err := tx.Clauses(clause.OnConflict{DoNothing: true}).Create(&order.Items).Error; err != nil {
					return fmt.Errorf("failed to insert order items: %w", err)
				}
			}
		}

		observability.LogInfoCtx("Finished order payload insertion", nil)
		return nil
	})
}
