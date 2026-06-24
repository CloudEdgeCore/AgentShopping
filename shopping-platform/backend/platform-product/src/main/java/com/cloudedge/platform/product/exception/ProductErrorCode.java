package com.cloudedge.platform.product.exception;

import com.cloudedge.platform.exception.ErrorCode;

public enum ProductErrorCode implements ErrorCode {

    CATEGORY_NOT_FOUND("P0001", "Category not found"),
    CATEGORY_NAME_EXISTS("P0002", "Category name already exists under current parent"),
    BRAND_NOT_FOUND("P0003", "Brand not found"),
    BRAND_NAME_EXISTS("P0004", "Brand name already exists"),
    PRODUCT_NOT_FOUND("P0005", "Product not found"),
    SKU_NOT_FOUND("P0006", "Sku not found"),
    SKU_REQUIRED("P0007", "At least one sku is required"),
    INVALID_PUBLISH_STATUS("P0008", "Invalid publish status"),
    DEFAULT_SKU_REQUIRED("P0009", "Only one default sku is allowed"),
    SKU_CODE_DUPLICATE("P0010", "Duplicate sku code in request"),
    CATEGORY_PARENT_NOT_FOUND("P0011", "Parent category not found"),
    CATEGORY_PARENT_INVALID("P0012", "Invalid parent category"),
    CATEGORY_IN_USE("P0013", "Category has related products and cannot be deleted"),
    BRAND_IN_USE("P0014", "Brand has related products and cannot be deleted"),
    PRODUCT_DELETE_PUBLISHED_FORBIDDEN("P0015", "Published product must be unpublished before deletion");

    private final String code;
    private final String message;

    ProductErrorCode(String code, String message) {
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
