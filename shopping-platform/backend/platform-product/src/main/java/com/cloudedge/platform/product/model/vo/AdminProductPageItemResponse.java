package com.cloudedge.platform.product.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class AdminProductPageItemResponse {

    private Long spuId;
    private String spuName;
    private String subtitle;
    private String coverImage;
    private Long categoryId;
    private String categoryName;
    private Long brandId;
    private String brandName;
    private Integer publishStatus;
    private Integer sort;
    private Integer skuCount;
    private BigDecimal minSalePrice;
    private BigDecimal maxSalePrice;
    private LocalDateTime updateTime;
}
