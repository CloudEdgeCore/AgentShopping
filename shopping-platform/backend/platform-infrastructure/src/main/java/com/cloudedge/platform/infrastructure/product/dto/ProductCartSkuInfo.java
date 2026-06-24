package com.cloudedge.platform.infrastructure.product.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class ProductCartSkuInfo {

    private Long skuId;
    private Long spuId;
    private Long categoryId;
    private String skuName;
    private String spuName;
    private String skuImage;
    private String skuAttrText;
    private BigDecimal salePrice;
}
