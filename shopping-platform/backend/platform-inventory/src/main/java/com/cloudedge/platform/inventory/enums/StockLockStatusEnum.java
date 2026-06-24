package com.cloudedge.platform.inventory.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum StockLockStatusEnum {

    LOCKED(1, "locked"),
    DEDUCTED(2, "deducted"),
    RELEASED(3, "released");

    private final Integer code;
    private final String desc;
}
