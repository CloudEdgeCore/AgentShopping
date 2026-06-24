package com.cloudedge.platform.order.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class OrderSettlementItemResponse {

    private Long skuId;
    private Long spuId;
    private String spuName;
    private String skuName;
    private String skuImage;
    private String skuAttrText;
    private Integer quantity;
    private BigDecimal originalPrice;
    private BigDecimal salePrice;
    private BigDecimal promotionAmount;
    private BigDecimal totalAmount;
    private Long promotionActivityId;
    private String promotionActivityName;
}
