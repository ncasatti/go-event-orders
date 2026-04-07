package orders

import "time"

// Client represents a customer in the system
type Client struct {
	ID        uint      `gorm:"primaryKey;autoIncrement" json:"id"`
	Name      string    `gorm:"size:255;not null" json:"name"`
	Email     string    `gorm:"size:255" json:"email"`
	Address   string    `gorm:"size:255" json:"address"`
	Phone     string    `gorm:"size:50" json:"phone"`
	IsActive  bool      `gorm:"default:true" json:"is_active"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

func (Client) TableName() string {
	return "clients"
}
