package orders

import (
	"context"
	"errors"
	"testing"
)

// Mock implementations for testing
type mockClientRepo struct {
	existsFunc   func(ctx context.Context, clientID uint) (bool, error)
	isActiveFunc func(ctx context.Context, clientID uint) (bool, error)
}

func (m *mockClientRepo) Exists(ctx context.Context, clientID uint) (bool, error) {
	if m.existsFunc != nil {
		return m.existsFunc(ctx, clientID)
	}
	return true, nil
}

func (m *mockClientRepo) IsActive(ctx context.Context, clientID uint) (bool, error) {
	if m.isActiveFunc != nil {
		return m.isActiveFunc(ctx, clientID)
	}
	return true, nil
}

type mockProductRepo struct {
	existsFunc   func(ctx context.Context, productID uint) (bool, error)
	isActiveFunc func(ctx context.Context, productID uint) (bool, error)
	getStockFunc func(ctx context.Context, productID uint) (int, error)
}

func (m *mockProductRepo) Exists(ctx context.Context, productID uint) (bool, error) {
	if m.existsFunc != nil {
		return m.existsFunc(ctx, productID)
	}
	return true, nil
}

func (m *mockProductRepo) IsActive(ctx context.Context, productID uint) (bool, error) {
	if m.isActiveFunc != nil {
		return m.isActiveFunc(ctx, productID)
	}
	return true, nil
}

func (m *mockProductRepo) GetStock(ctx context.Context, productID uint) (int, error) {
	if m.getStockFunc != nil {
		return m.getStockFunc(ctx, productID)
	}
	return 100, nil
}

// Helper function to create a valid order for testing
func createValidOrder() *Order {
	return &Order{
		ClientID: 1,
		Items: []OrderItem{
			{
				ProductID: 1,
				Quantity:  5,
			},
		},
	}
}

func TestOrderValidator_ValidateOrder_Success(t *testing.T) {
	clientRepo := &mockClientRepo{}
	productRepo := &mockProductRepo{}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	result := validator.ValidateOrder(context.Background(), order)

	if !result.IsValid {
		t.Errorf("Expected valid order, got errors: %v", result.Errors)
	}
	if len(result.Errors) != 0 {
		t.Errorf("Expected no errors, got %d", len(result.Errors))
	}
}

func TestOrderValidator_ValidateOrder_ClientNotExists(t *testing.T) {
	clientRepo := &mockClientRepo{
		existsFunc: func(ctx context.Context, clientID uint) (bool, error) {
			return false, nil
		},
	}
	productRepo := &mockProductRepo{}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when client doesn't exist")
	}
	if len(result.Errors) == 0 {
		t.Error("Expected errors but got none")
	}
}

func TestOrderValidator_ValidateOrder_ClientInactive(t *testing.T) {
	clientRepo := &mockClientRepo{
		isActiveFunc: func(ctx context.Context, clientID uint) (bool, error) {
			return false, nil
		},
	}
	productRepo := &mockProductRepo{}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when client is inactive")
	}
	if len(result.Errors) == 0 {
		t.Error("Expected errors but got none")
	}
}

func TestOrderValidator_ValidateOrder_NoClientID(t *testing.T) {
	clientRepo := &mockClientRepo{}
	productRepo := &mockProductRepo{}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	order.ClientID = 0
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when client_id is 0")
	}
}

func TestOrderValidator_ValidateOrder_NoItems(t *testing.T) {
	clientRepo := &mockClientRepo{}
	productRepo := &mockProductRepo{}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	order.Items = []OrderItem{}
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when there are no items")
	}
}

func TestOrderValidator_ValidateOrder_ProductNotExists(t *testing.T) {
	clientRepo := &mockClientRepo{}
	productRepo := &mockProductRepo{
		existsFunc: func(ctx context.Context, productID uint) (bool, error) {
			return false, nil
		},
	}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when product doesn't exist")
	}
}

func TestOrderValidator_ValidateOrder_ProductInactive(t *testing.T) {
	clientRepo := &mockClientRepo{}
	productRepo := &mockProductRepo{
		isActiveFunc: func(ctx context.Context, productID uint) (bool, error) {
			return false, nil
		},
	}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when product is inactive")
	}
}

func TestOrderValidator_ValidateOrder_InsufficientStock(t *testing.T) {
	clientRepo := &mockClientRepo{}
	productRepo := &mockProductRepo{
		getStockFunc: func(ctx context.Context, productID uint) (int, error) {
			return 2, nil // Less than requested quantity (5)
		},
	}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when stock is insufficient")
	}
}

func TestOrderValidator_ValidateOrder_InvalidQuantity(t *testing.T) {
	clientRepo := &mockClientRepo{}
	productRepo := &mockProductRepo{}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	order.Items[0].Quantity = 0
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when quantity is 0")
	}
}

func TestOrderValidator_ValidateOrder_RepositoryError(t *testing.T) {
	clientRepo := &mockClientRepo{
		existsFunc: func(ctx context.Context, clientID uint) (bool, error) {
			return false, errors.New("database error")
		},
	}
	productRepo := &mockProductRepo{}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	result := validator.ValidateOrder(context.Background(), order)

	if result.IsValid {
		t.Error("Expected invalid order when repository returns error")
	}
}

func TestOrderValidator_ValidateOrder_MultipleItems(t *testing.T) {
	clientRepo := &mockClientRepo{}
	productRepo := &mockProductRepo{}
	validator := NewOrderValidator(clientRepo, productRepo)

	order := createValidOrder()
	order.Items = append(order.Items, OrderItem{
		ProductID: 2,
		Quantity:  10,
	})

	result := validator.ValidateOrder(context.Background(), order)

	if !result.IsValid {
		t.Errorf("Expected valid order with multiple items, got errors: %v", result.Errors)
	}
}
