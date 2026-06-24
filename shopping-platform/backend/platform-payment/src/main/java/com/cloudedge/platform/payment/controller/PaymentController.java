package com.cloudedge.platform.payment.controller;

import com.cloudedge.platform.payment.model.dto.PaymentCreateRequest;
import com.cloudedge.platform.payment.model.vo.PaymentCreateResponse;
import com.cloudedge.platform.payment.model.vo.PaymentDetailResponse;
import com.cloudedge.platform.payment.service.PaymentService;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/payments")
public class PaymentController {

    @Autowired
    private PaymentService paymentService;

    @PostMapping("/mock/create")
    public Result<PaymentCreateResponse> createMockPayment(@Valid @RequestBody PaymentCreateRequest request) {
        return Result.success(paymentService.createMockPayment(request));
    }

    @GetMapping("/{paymentNo}")
    public Result<PaymentDetailResponse> getPaymentDetail(@PathVariable String paymentNo) {
        return Result.success(paymentService.getPaymentDetail(paymentNo));
    }

    @GetMapping("/order/{orderNo}")
    public Result<PaymentDetailResponse> getPaymentByOrderNo(@PathVariable String orderNo) {
        return Result.success(paymentService.getPaymentByOrderNo(orderNo));
    }

    @PostMapping("/{paymentNo}/success")
    public Result<PaymentDetailResponse> mockPaySuccess(@PathVariable String paymentNo) {
        return Result.success(paymentService.mockPaySuccess(paymentNo));
    }
}
