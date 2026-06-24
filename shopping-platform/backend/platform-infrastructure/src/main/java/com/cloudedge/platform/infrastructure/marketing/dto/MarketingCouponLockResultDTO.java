package com.cloudedge.platform.infrastructure.marketing.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class MarketingCouponLockResultDTO {

    private Long userCouponId;
    private String couponCode;
    private String couponName;
    private BigDecimal couponAmount;
}
