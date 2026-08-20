package com.cloudedge.platform.marketing.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class AvailableCouponResponse {

    private Long id;
    private String name;
    private Integer couponType;
    private BigDecimal thresholdAmount;
    private BigDecimal discountAmount;
    private BigDecimal discountRate;
    private Integer scopeType;
    private Integer totalCount;
    private Integer claimedCount;
    private Integer remainCount;
    private Integer perUserLimit;
    private Integer userClaimedCount;
    private LocalDateTime receiveStartTime;
    private LocalDateTime receiveEndTime;
    private LocalDateTime validFrom;
    private LocalDateTime validTo;
    private String description;
    private Integer status;
}
