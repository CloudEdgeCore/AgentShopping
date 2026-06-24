package com.cloudedge.platform.product.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class ProductSkuResponse {

    private Long skuId;
    private String skuCode;
    private String skuName;
    private String imageUrl;
    private BigDecimal salePrice;
    private BigDecimal marketPrice;
    private BigDecimal promotionPrice;
    private Long promotionActivityId;
    private String promotionActivityName;
    private String attrText;
    private Integer totalStock;
    private Boolean defaultSku;
    private Integer status;
}
