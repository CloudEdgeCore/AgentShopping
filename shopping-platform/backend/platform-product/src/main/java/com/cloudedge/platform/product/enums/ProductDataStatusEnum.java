package com.cloudedge.platform.product.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum ProductDataStatusEnum {

    DISABLED(0, "disabled"),
    ENABLED(1, "enabled");

    private final Integer code;
    private final String desc;
}
