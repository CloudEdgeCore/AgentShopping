package com.cloudedge.platform.cart.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
public class CartListResponse {
    private List<CartItemResponse> items;
    private Integer totalItemCount;
    private Integer checkedItemCount;
    private BigDecimal checkedAmount;
}
