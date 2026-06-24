package com.cloudedge.platform.payment.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum PaymentChannelEnum {

    MOCK(10, "mock");

    private final Integer code;
    private final String desc;
}
