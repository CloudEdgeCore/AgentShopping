package com.cloudedge.platform.marketing.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum CouponScopeTypeEnum {

    ALL(10, "all"),
    CATEGORY(20, "category"),
    SPU(30, "spu"),
    SKU(40, "sku");

    private final Integer code;
    private final String desc;
}
