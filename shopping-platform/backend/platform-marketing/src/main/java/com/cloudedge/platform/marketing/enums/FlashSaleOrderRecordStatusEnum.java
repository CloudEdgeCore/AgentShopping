package com.cloudedge.platform.marketing.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum FlashSaleOrderRecordStatusEnum {

    LOCKED(10, "locked"),
    USED(20, "used"),
    RELEASED(30, "released");

    private final Integer code;
    private final String desc;
}
