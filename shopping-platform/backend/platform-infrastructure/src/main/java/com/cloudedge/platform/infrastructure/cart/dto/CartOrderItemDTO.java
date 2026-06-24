package com.cloudedge.platform.infrastructure.cart.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class CartOrderItemDTO {

    private Long cartItemId;
    private Long skuId;
    private Integer quantity;
}
