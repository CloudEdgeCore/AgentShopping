package com.cloudedge.platform.inventory.exception;

import com.cloudedge.platform.exception.ErrorCode;

public enum InventoryErrorCode implements ErrorCode {

    STOCK_NOT_FOUND("INV0001", "Stock record not found"),
    STOCK_NOT_ENOUGH("INV0002", "Stock not enough"),
    INVALID_TOTAL_STOCK("INV0003", "Total stock cannot be less than locked stock"),
    STOCK_ALREADY_EXISTS("INV0004", "Stock record already exists"),
    LOCK_ITEMS_EMPTY("INV0005", "Lock item list cannot be empty"),
    INVALID_LOCK_QUANTITY("INV0006", "Lock quantity must be greater than 0"),
    STOCK_OPERATION_FAILED("INV0007", "Stock operation failed"),
    STOCK_HAS_LOCKED_RECORDS("INV0008", "Stock with locked records cannot be deleted");

    private final String code;
    private final String message;

    InventoryErrorCode(String code, String message) {
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
