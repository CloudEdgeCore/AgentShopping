package com.cloudedge.platform.product.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ProductPublishRequest {

    @NotNull(message = "publish status cannot be null")
    @Min(value = 0, message = "publish status must be 0 or 1")
    @Max(value = 1, message = "publish status must be 0 or 1")
    private Integer publishStatus;
}
