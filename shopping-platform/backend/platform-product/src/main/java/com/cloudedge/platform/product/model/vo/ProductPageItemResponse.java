package com.cloudedge.platform.product.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class ProductPageItemResponse {

    private Long spuId;
    private String spuName;
    private String subtitle;
    private String coverImage;
    private Long categoryId;
    private String categoryName;
    private Long brandId;
    private String brandName;
    private BigDecimal minSalePrice;
    private BigDecimal maxSalePrice;
    private BigDecimal minPromotionPrice;
    private BigDecimal maxPromotionPrice;
}
