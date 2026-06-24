package com.cloudedge.platform.marketing.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum CouponUserStatusEnum {

    UNUSED(10, "unused"),
    LOCKED(15, "locked"),
    USED(20, "used"),
    EXPIRED(30, "expired");

    private final Integer code;
    private final String desc;
}
