package com.cloudedge.platform.cart.exception;

import com.cloudedge.platform.exception.ErrorCode;

public enum CartErrorCode implements ErrorCode {
    CART_ITEM_NOT_FOUND("CART0001", "Cart item not found"),
    SKU_NOT_SALEABLE("CART0002", "SKU not saleable"),
    INVALID_QUANTITY("CART0003", "Invalid quantity");

    private final String code;
    private final String message;

    CartErrorCode(String code, String message) {
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
