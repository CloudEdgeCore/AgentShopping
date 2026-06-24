package com.cloudedge.platform.inventory.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class StockUpdateRequest {
    @NotNull(message = "totalStock cannot be null")
    @Min(value = 0, message = "totalStock cannot be negative")
    @Max(value = 999999999, message = "totalStock is too large")
    private Integer totalStock;

    @NotNull(message = "status cannot be null")
    @Min(value = 0, message = "status must be 0 or 1")
    @Max(value = 1, message = "status must be 0 or 1")
    private Integer status;
}
