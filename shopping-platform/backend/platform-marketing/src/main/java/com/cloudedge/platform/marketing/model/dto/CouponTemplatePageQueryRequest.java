package com.cloudedge.platform.marketing.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

@Data
public class CouponTemplatePageQueryRequest {

    @Min(value = 1, message = "current must be greater than 0")
    private long current = 1;

    @Min(value = 1, message = "size must be greater than 0")
    @Max(value = 100, message = "size cannot exceed 100")
    private long size = 10;

    private Integer status;
}
