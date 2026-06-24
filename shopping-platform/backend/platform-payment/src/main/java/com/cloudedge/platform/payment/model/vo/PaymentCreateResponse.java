package com.cloudedge.platform.payment.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class PaymentCreateResponse {

    private String paymentNo;
    private String orderNo;
    private Integer payChannel;
    private Integer payStatus;
    private BigDecimal amount;
    private String subject;
    private String mockPayUrl;
}
