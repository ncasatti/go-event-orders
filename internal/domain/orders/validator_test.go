package orders

import "testing"

func TestValidationResult_NewValidationResult(t *testing.T) {
	result := NewValidationResult()

	if !result.IsValid {
		t.Error("New validation result should be valid")
	}
	if len(result.Errors) != 0 {
		t.Error("New validation result should have no errors")
	}
}

func TestValidationResult_AddError(t *testing.T) {
	result := NewValidationResult()

	result.AddError("test error")

	if result.IsValid {
		t.Error("Validation result should be invalid after adding error")
	}
	if len(result.Errors) != 1 {
		t.Errorf("Expected 1 error, got %d", len(result.Errors))
	}
	if result.Errors[0] != "test error" {
		t.Errorf("Expected 'test error', got '%s'", result.Errors[0])
	}
}

func TestValidationResult_HasErrors(t *testing.T) {
	result := NewValidationResult()

	if result.HasErrors() {
		t.Error("New validation result should not have errors")
	}

	result.AddError("error")

	if !result.HasErrors() {
		t.Error("Validation result should have errors after adding one")
	}
}
