package com.cloudedge.platform.infrastructure.marketing.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class MarketingSkuDiscountDTO {

    private Long skuId;
    private Long activityId;
    private String activityName;
    private BigDecimal discountPrice;
}
