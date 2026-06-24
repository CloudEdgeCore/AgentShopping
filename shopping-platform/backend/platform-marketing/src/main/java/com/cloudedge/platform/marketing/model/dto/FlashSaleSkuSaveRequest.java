package com.cloudedge.platform.marketing.model.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class FlashSaleSkuSaveRequest {

    @NotNull(message = "skuId cannot be null")
    private Long skuId;

    @NotNull(message = "originalPrice cannot be null")
    @DecimalMin(value = "0.01", message = "originalPrice must be greater than 0")
    private BigDecimal originalPrice;

    @NotNull(message = "discountPrice cannot be null")
    @DecimalMin(value = "0.01", message = "discountPrice must be greater than 0")
    private BigDecimal discountPrice;

    @NotNull(message = "activityStock cannot be null")
    @Min(value = 1, message = "activityStock must be greater than 0")
    @Max(value = 9999999, message = "activityStock is too large")
    private Integer activityStock;

    @NotNull(message = "perUserLimit cannot be null")
    @Min(value = 1, message = "perUserLimit must be greater than 0")
    @Max(value = 100, message = "perUserLimit is too large")
    private Integer perUserLimit;

    private Integer sort = 0;
}
