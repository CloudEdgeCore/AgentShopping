package com.cloudedge.platform.order.model.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.List;

public class OrderSubmitRequest {

    @NotNull(message = "addressId cannot be null")
    private Long addressId;

    @Valid
    private List<OrderSubmitItemRequest> items;

    private List<Long> cartItemIds;

    private Long userCouponId;

    @Size(max = 500, message = "remark length cannot exceed 500")
    private String remark;

    public Long getAddressId() {
        return addressId;
    }

    public void setAddressId(Long addressId) {
        this.addressId = addressId;
    }

    public List<OrderSubmitItemRequest> getItems() {
        return items;
    }

    public void setItems(List<OrderSubmitItemRequest> items) {
        this.items = items;
    }

    public List<Long> getCartItemIds() {
        return cartItemIds;
    }

    public void setCartItemIds(List<Long> cartItemIds) {
        this.cartItemIds = cartItemIds;
    }

    public Long getUserCouponId() {
        return userCouponId;
    }

    public void setUserCouponId(Long userCouponId) {
        this.userCouponId = userCouponId;
    }

    public String getRemark() {
        return remark;
    }

    public void setRemark(String remark) {
        this.remark = remark;
    }
}
