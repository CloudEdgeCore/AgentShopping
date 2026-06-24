package com.cloudedge.platform.order.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
public class OrderSettlementPreviewResponse {

    private Integer totalQuantity;
    private BigDecimal totalAmount;
    private BigDecimal promotionAmount;
    private BigDecimal couponAmount;
    private BigDecimal payableAmount;
    private OrderSettlementCouponResponse selectedCoupon;
    private List<OrderSettlementCouponResponse> availableCoupons;
    private List<OrderSettlementItemResponse> items;
}
