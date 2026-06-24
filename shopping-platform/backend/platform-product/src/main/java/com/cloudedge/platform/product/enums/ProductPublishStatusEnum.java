package com.cloudedge.platform.product.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum ProductPublishStatusEnum {

    UNPUBLISHED(0, "unpublished"),
    PUBLISHED(1, "published");

    private final Integer code;
    private final String desc;
}
