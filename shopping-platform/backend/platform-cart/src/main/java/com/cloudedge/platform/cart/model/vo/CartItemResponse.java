package com.cloudedge.platform.cart.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class CartItemResponse {
    private Long id;
    private Long skuId;
    private Long spuId;
    private String spuName;
    private String skuName;
    private String skuImage;
    private String skuAttrText;
    private BigDecimal salePrice;
    private BigDecimal currentSalePrice;
    private Integer quantity;
    private Boolean checked;
    private Boolean productAvailable;
    private Boolean priceChanged;
    private BigDecimal lineAmount;
}
