package com.cloudedge.platform.infrastructure.payment.service;

public interface PaymentOrderService {

    void closeUnpaidPaymentByOrderNo(String orderNo, String closeReason);
}
