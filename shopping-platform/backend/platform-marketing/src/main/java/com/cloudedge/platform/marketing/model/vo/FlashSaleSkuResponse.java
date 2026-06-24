package com.cloudedge.platform.marketing.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class FlashSaleSkuResponse {

    private Long skuId;
    private BigDecimal originalPrice;
    private BigDecimal discountPrice;
    private Integer activityStock;
    private Integer lockedStock;
    private Integer perUserLimit;
    private Integer sort;
}
