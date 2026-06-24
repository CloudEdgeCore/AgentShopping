package com.cloudedge.platform.marketing.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class UserCouponResponse {

    private Long id;
    private Long templateId;
    private String couponCode;
    private String couponName;
    private Integer couponType;
    private BigDecimal thresholdAmount;
    private BigDecimal discountAmount;
    private BigDecimal discountRate;
    private Integer scopeType;
    private Integer status;
    private LocalDateTime receiveTime;
    private LocalDateTime validFrom;
    private LocalDateTime validTo;
    private LocalDateTime useTime;
    private String orderNo;
}
