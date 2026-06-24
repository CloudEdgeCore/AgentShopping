package com.cloudedge.platform.payment.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class PaymentDetailResponse {

    private String paymentNo;
    private String orderNo;
    private Integer payChannel;
    private Integer payStatus;
    private BigDecimal amount;
    private String subject;
    private LocalDateTime successTime;
    private LocalDateTime closeTime;
    private String closeReason;
    private LocalDateTime createTime;
}
