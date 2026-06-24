package com.cloudedge.platform.order.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum OrderStatusEnum {

    PENDING_PAYMENT(10, "pending_payment"),
    PAID(20, "paid"),
    CANCELLED(30, "cancelled");

    private final Integer code;
    private final String desc;
}
