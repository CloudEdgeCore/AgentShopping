package com.cloudedge.platform.marketing.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class CouponTemplateResponse {

    private Long id;
    private String name;
    private Integer couponType;
    private BigDecimal thresholdAmount;
    private BigDecimal discountAmount;
    private BigDecimal discountRate;
    private Integer totalCount;
    private Integer claimedCount;
    private Integer perUserLimit;
    private Integer scopeType;
    private List<Long> scopeIds;
    private LocalDateTime receiveStartTime;
    private LocalDateTime receiveEndTime;
    private LocalDateTime validFrom;
    private LocalDateTime validTo;
    private String description;
    private Integer status;
}
