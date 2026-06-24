package com.cloudedge.platform.order.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

public class OrderSubmitItemRequest {

    @NotNull(message = "skuId cannot be null")
    private Long skuId;

    @NotNull(message = "quantity cannot be null")
    @Min(value = 1, message = "quantity must be greater than 0")
    @Max(value = 999999, message = "quantity is too large")
    private Integer quantity;

    public Long getSkuId() {
        return skuId;
    }

    public void setSkuId(Long skuId) {
        this.skuId = skuId;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }
}
