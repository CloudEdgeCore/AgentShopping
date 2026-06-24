package com.cloudedge.platform.marketing.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum CouponTemplateStatusEnum {

    DISABLED(0, "disabled"),
    ENABLED(1, "enabled");

    private final Integer code;
    private final String desc;
}
