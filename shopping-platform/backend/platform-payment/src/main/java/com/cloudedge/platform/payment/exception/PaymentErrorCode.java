package com.cloudedge.platform.payment.exception;

import com.cloudedge.platform.exception.ErrorCode;

public enum PaymentErrorCode implements ErrorCode {

    PAYMENT_NOT_FOUND("PAY0001", "Payment not found"),
    ORDER_NOT_FOUND("PAY0002", "Order not found"),
    ORDER_NOT_PAYABLE("PAY0003", "Order is not payable"),
    PAYMENT_STATUS_INVALID("PAY0004", "Payment status is invalid");

    private final String code;
    private final String message;

    PaymentErrorCode(String code, String message) {
        this.code = code;
        this.message = message;
    }

    @Override
    public String getCode() {
        return code;
    }

    @Override
    public String getMessage() {
        return message;
    }
}
