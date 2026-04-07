package orders

import "time"

// Order represents a sales order
type Order struct {
	ID          uint        `gorm:"primaryKey;autoIncrement" json:"id"`
	ClientID    uint        `gorm:"not null;index" json:"client_id"`
	Client      Client      `gorm:"foreignKey:ClientID" json:"client,omitempty"`
	OrderDate   time.Time   `gorm:"not null" json:"order_date"`
	TotalAmount float64     `gorm:"type:decimal(10,2);not null" json:"total_amount"`
	Status      string      `gorm:"size:50;default:'pending'" json:"status"`
	Items       []OrderItem `gorm:"foreignKey:OrderID" json:"items"`
	CreatedAt   time.Time   `json:"created_at"`
	UpdatedAt   time.Time   `json:"updated_at"`
}

func (Order) TableName() string {
	return "orders"
}

// OrderItem represents a line item in an order
type OrderItem struct {
	ID        uint    `gorm:"primaryKey;autoIncrement" json:"id"`
	OrderID   uint    `gorm:"not null;index" json:"order_id"`
	ProductID uint    `gorm:"not null;index" json:"product_id"`
	Product   Product `gorm:"foreignKey:ProductID" json:"product,omitempty"`
	Quantity  int     `gorm:"not null" json:"quantity"`
	UnitPrice float64 `gorm:"type:decimal(10,2);not null" json:"unit_price"`
	Subtotal  float64 `gorm:"type:decimal(10,2);not null" json:"subtotal"`
}

func (OrderItem) TableName() string {
	return "order_items"
}
