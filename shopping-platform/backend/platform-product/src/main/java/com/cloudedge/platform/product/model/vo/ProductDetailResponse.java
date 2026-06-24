package com.cloudedge.platform.product.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
public class ProductDetailResponse {

    private Long spuId;
    private String spuName;
    private String subtitle;
    private String coverImage;
    private Long categoryId;
    private String categoryName;
    private Long brandId;
    private String brandName;
    private List<String> albumImages;
    private String detail;
    private BigDecimal minSalePrice;
    private BigDecimal maxSalePrice;
    private BigDecimal minPromotionPrice;
    private BigDecimal maxPromotionPrice;
    private List<ProductSkuResponse> skuList;
}
