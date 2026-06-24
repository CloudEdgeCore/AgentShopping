package com.cloudedge.platform.marketing.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum CouponTypeEnum {

    FULL_REDUCTION(10, "full_reduction"),
    DISCOUNT(20, "discount");

    private final Integer code;
    private final String desc;
}
