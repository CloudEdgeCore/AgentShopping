package com.cloudedge.platform.infrastructure.marketing.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class MarketingOrderItemDTO {

    private Long skuId;
    private Long spuId;
    private Long categoryId;
    private Integer quantity;
    private BigDecimal amount;
}
