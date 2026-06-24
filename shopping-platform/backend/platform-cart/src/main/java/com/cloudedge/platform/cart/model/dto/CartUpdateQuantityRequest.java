package com.cloudedge.platform.cart.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CartUpdateQuantityRequest {

    @NotNull(message = "quantity cannot be null")
    @Min(value = 1, message = "quantity must be greater than 0")
    @Max(value = 999, message = "quantity cannot exceed 999")
    private Integer quantity;
}
