package repository

import (
	"context"

	"gorm.io/gorm"
)

// ValidationRepository provides data access for validation operations
type ValidationRepository struct {
	db *gorm.DB
}

// NewValidationRepository creates a new validation repository
func NewValidationRepository(db *gorm.DB) *ValidationRepository {
	return &ValidationRepository{db: db}
}

// ClientExists checks if a client exists
func (r *ValidationRepository) ClientExists(ctx context.Context, clientID uint) (bool, error) {
	var count int64
	err := r.db.WithContext(ctx).Table("clients").Where("id = ?", clientID).Count(&count).Error
	return count > 0, err
}

// ClientIsActive checks if a client is active
func (r *ValidationRepository) ClientIsActive(ctx context.Context, clientID uint) (bool, error) {
	var isActive bool
	err := r.db.WithContext(ctx).Table("clients").Select("is_active").Where("id = ?", clientID).Scan(&isActive).Error
	return isActive, err
}

// ProductExists checks if a product exists
func (r *ValidationRepository) ProductExists(ctx context.Context, productID uint) (bool, error) {
	var count int64
	err := r.db.WithContext(ctx).Table("products").Where("id = ?", productID).Count(&count).Error
	return count > 0, err
}

// ProductIsActive checks if a product is active
func (r *ValidationRepository) ProductIsActive(ctx context.Context, productID uint) (bool, error) {
	var isActive bool
	err := r.db.WithContext(ctx).Table("products").Select("is_active").Where("id = ?", productID).Scan(&isActive).Error
	return isActive, err
}

// ProductGetStock retrieves the stock for a product
func (r *ValidationRepository) ProductGetStock(ctx context.Context, productID uint) (int, error) {
	var stock int
	err := r.db.WithContext(ctx).Table("products").Select("stock").Where("id = ?", productID).Scan(&stock).Error
	return stock, err
}

// ClientRepositoryAdapter adapts ValidationRepository to ClientRepository interface
type ClientRepositoryAdapter struct {
	repo *ValidationRepository
}

// NewClientRepositoryAdapter creates a new client repository adapter
func NewClientRepositoryAdapter(repo *ValidationRepository) *ClientRepositoryAdapter {
	return &ClientRepositoryAdapter{repo: repo}
}

// Exists checks if a client exists
func (a *ClientRepositoryAdapter) Exists(ctx context.Context, clientID uint) (bool, error) {
	return a.repo.ClientExists(ctx, clientID)
}

// IsActive checks if a client is active
func (a *ClientRepositoryAdapter) IsActive(ctx context.Context, clientID uint) (bool, error) {
	return a.repo.ClientIsActive(ctx, clientID)
}

// ProductRepositoryAdapter adapts ValidationRepository to ProductRepository interface
type ProductRepositoryAdapter struct {
	repo *ValidationRepository
}

// NewProductRepositoryAdapter creates a new product repository adapter
func NewProductRepositoryAdapter(repo *ValidationRepository) *ProductRepositoryAdapter {
	return &ProductRepositoryAdapter{repo: repo}
}

// Exists checks if a product exists
func (a *ProductRepositoryAdapter) Exists(ctx context.Context, productID uint) (bool, error) {
	return a.repo.ProductExists(ctx, productID)
}

// IsActive checks if a product is active
func (a *ProductRepositoryAdapter) IsActive(ctx context.Context, productID uint) (bool, error) {
	return a.repo.ProductIsActive(ctx, productID)
}

// GetStock retrieves the stock for a product
func (a *ProductRepositoryAdapter) GetStock(ctx context.Context, productID uint) (int, error) {
	return a.repo.ProductGetStock(ctx, productID)
}
