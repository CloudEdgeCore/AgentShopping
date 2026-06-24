package com.cloudedge.platform.payment.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum PaymentStatusEnum {

    UNPAID(10, "unpaid"),
    SUCCESS(20, "success"),
    CLOSED(30, "closed");

    private final Integer code;
    private final String desc;
}
