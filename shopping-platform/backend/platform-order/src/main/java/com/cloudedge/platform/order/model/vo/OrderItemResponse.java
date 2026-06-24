package com.cloudedge.platform.order.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class OrderItemResponse {

    private Long skuId;
    private Long spuId;
    private String spuName;
    private String skuName;
    private String skuImage;
    private String skuAttrText;
    private BigDecimal originalPrice;
    private BigDecimal salePrice;
    private Integer quantity;
    private BigDecimal promotionAmount;
    private BigDecimal totalAmount;
}
