package com.cloudedge.platform.infrastructure.marketing.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class MarketingCouponPreviewDTO {

    private Long userCouponId;
    private String couponCode;
    private String couponName;
    private Integer couponType;
    private BigDecimal thresholdAmount;
    private BigDecimal couponAmount;
    private LocalDateTime validTo;
}
