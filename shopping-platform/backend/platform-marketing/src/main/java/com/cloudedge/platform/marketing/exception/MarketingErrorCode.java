package com.cloudedge.platform.marketing.exception;

import com.cloudedge.platform.exception.ErrorCode;

public enum MarketingErrorCode implements ErrorCode {

    COUPON_TEMPLATE_NOT_FOUND("MKT0001", "Coupon template not found"),
    COUPON_TEMPLATE_NOT_RECEIVABLE("MKT0002", "Coupon template is not receivable"),
    COUPON_TEMPLATE_OUT_OF_STOCK("MKT0003", "Coupon template is out of stock"),
    COUPON_USER_LIMIT_REACHED("MKT0004", "Coupon user limit reached"),
    INVALID_COUPON_SCOPE("MKT0005", "Invalid coupon scope"),
    INVALID_COUPON_AMOUNT("MKT0006", "Invalid coupon amount"),
    FLASH_SALE_ACTIVITY_NOT_FOUND("MKT0007", "Flash sale activity not found"),
    INVALID_ACTIVITY_TIME("MKT0008", "Invalid activity time range"),
    INVALID_FLASH_SALE_ITEM("MKT0009", "Invalid flash sale item");

    private final String code;
    private final String message;

    MarketingErrorCode(String code, String message) {
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
