package com.cloudedge.platform.payment.service;

import com.cloudedge.platform.payment.model.dto.PaymentCreateRequest;
import com.cloudedge.platform.payment.model.vo.PaymentCreateResponse;
import com.cloudedge.platform.payment.model.vo.PaymentDetailResponse;

public interface PaymentService {

    PaymentCreateResponse createMockPayment(PaymentCreateRequest request);

    PaymentDetailResponse getPaymentDetail(String paymentNo);

    PaymentDetailResponse getPaymentByOrderNo(String orderNo);

    PaymentDetailResponse mockPaySuccess(String paymentNo);
}
