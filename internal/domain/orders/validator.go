package orders

// ValidationResult represents the result of a validation operation
type ValidationResult struct {
	IsValid bool
	Errors  []string
}

// NewValidationResult creates a new validation result
func NewValidationResult() *ValidationResult {
	return &ValidationResult{
		IsValid: true,
		Errors:  []string{},
	}
}

// AddError adds an error to the validation result
func (vr *ValidationResult) AddError(err string) {
	vr.IsValid = false
	vr.Errors = append(vr.Errors, err)
}

// HasErrors returns true if there are validation errors
func (vr *ValidationResult) HasErrors() bool {
	return !vr.IsValid
}
