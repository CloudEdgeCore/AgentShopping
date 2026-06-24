package com.cloudedge.platform.order.exception;

import com.cloudedge.platform.exception.ErrorCode;

public enum OrderErrorCode implements ErrorCode {

    ORDER_NOT_FOUND("ORD0001", "Order not found"),
    ORDER_ITEM_EMPTY("ORD0002", "Order item list cannot be empty"),
    INVALID_ORDER_QUANTITY("ORD0003", "Order quantity must be greater than 0"),
    ADDRESS_NOT_FOUND("ORD0004", "Address not found"),
    PRODUCT_NOT_SALEABLE("ORD0005", "Product is not saleable"),
    STOCK_NOT_ENOUGH("ORD0006", "Stock not enough"),
    ORDER_STATUS_INVALID("ORD0007", "Order status is invalid"),
    CART_ITEM_NOT_FOUND("ORD0008", "Cart item not found");

    private final String code;
    private final String message;

    OrderErrorCode(String code, String message) {
        this.code = code;
        this.message = message;
    }

    @Override
    public String getCode() {
        return code;
    }

    @Override
    public String getMessage() {
        return message;
    }
}
