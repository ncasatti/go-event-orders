package orders

import (
	"context"
	"fmt"
)

// ClientRepository defines the interface for client data access
type ClientRepository interface {
	Exists(ctx context.Context, clientID uint) (bool, error)
	IsActive(ctx context.Context, clientID uint) (bool, error)
}

// ProductRepository defines the interface for product data access
type ProductRepository interface {
	Exists(ctx context.Context, productID uint) (bool, error)
	IsActive(ctx context.Context, productID uint) (bool, error)
	GetStock(ctx context.Context, productID uint) (int, error)
}

// OrderValidator handles business validation for orders
type OrderValidator struct {
	clientRepo  ClientRepository
	productRepo ProductRepository
}

// NewOrderValidator creates a new order validator
func NewOrderValidator(clientRepo ClientRepository, productRepo ProductRepository) *OrderValidator {
	return &OrderValidator{
		clientRepo:  clientRepo,
		productRepo: productRepo,
	}
}

// ValidateOrder performs comprehensive validation on an order
func (v *OrderValidator) ValidateOrder(ctx context.Context, order *Order) *ValidationResult {
	result := NewValidationResult()

	// Validate client
	if order.ClientID == 0 {
		result.AddError("client_id is required")
	} else {
		exists, err := v.clientRepo.Exists(ctx, order.ClientID)
		if err != nil {
			result.AddError(fmt.Sprintf("error checking client existence: %v", err))
		} else if !exists {
			result.AddError(fmt.Sprintf("client with ID %d does not exist", order.ClientID))
		} else {
			active, err := v.clientRepo.IsActive(ctx, order.ClientID)
			if err != nil {
				result.AddError(fmt.Sprintf("error checking client status: %v", err))
			} else if !active {
				result.AddError(fmt.Sprintf("client with ID %d is not active", order.ClientID))
			}
		}
	}

	// Validate order items
	if len(order.Items) == 0 {
		result.AddError("order must have at least one item")
	}

	for i, item := range order.Items {
		v.validateOrderItem(ctx, &item, i, result)
	}

	return result
}

// validateOrderItem validates a single order item
func (v *OrderValidator) validateOrderItem(ctx context.Context, item *OrderItem, index int, result *ValidationResult) {
	prefix := fmt.Sprintf("item[%d]", index)

	// Validate product
	if item.ProductID == 0 {
		result.AddError(fmt.Sprintf("%s: product_id is required", prefix))
		return
	}

	exists, err := v.productRepo.Exists(ctx, item.ProductID)
	if err != nil {
		result.AddError(fmt.Sprintf("%s: error checking product existence: %v", prefix, err))
		return
	}
	if !exists {
		result.AddError(fmt.Sprintf("%s: product with ID %d does not exist", prefix, item.ProductID))
		return
	}

	active, err := v.productRepo.IsActive(ctx, item.ProductID)
	if err != nil {
		result.AddError(fmt.Sprintf("%s: error checking product status: %v", prefix, err))
		return
	}
	if !active {
		result.AddError(fmt.Sprintf("%s: product with ID %d is not active", prefix, item.ProductID))
		return
	}

	// Validate quantity
	if item.Quantity <= 0 {
		result.AddError(fmt.Sprintf("%s: quantity must be greater than 0", prefix))
		return
	}

	// Validate stock
	stock, err := v.productRepo.GetStock(ctx, item.ProductID)
	if err != nil {
		result.AddError(fmt.Sprintf("%s: error checking product stock: %v", prefix, err))
		return
	}
	if item.Quantity > stock {
		result.AddError(fmt.Sprintf("%s: insufficient stock for product %d (requested: %d, available: %d)",
			prefix, item.ProductID, item.Quantity, stock))
	}
}
