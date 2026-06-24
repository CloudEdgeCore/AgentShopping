package com.cloudedge.platform.marketing.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class SkuDiscountResponse {

    private Long skuId;
    private Long activityId;
    private String activityName;
    private BigDecimal originalPrice;
    private BigDecimal discountPrice;
    private Integer activityStock;
    private Integer lockedStock;
    private Integer perUserLimit;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
}
