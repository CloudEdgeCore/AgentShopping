package com.cloudedge.platform.product.model.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.math.BigDecimal;

@Data
public class ProductSkuSaveRequest {

    @Size(max = 64, message = "sku code length cannot exceed 64")
    private String skuCode;

    @NotBlank(message = "sku name cannot be blank")
    @Size(max = 128, message = "sku name length cannot exceed 128")
    private String skuName;

    @Size(max = 255, message = "sku image length cannot exceed 255")
    private String imageUrl;

    @NotNull(message = "sale price cannot be null")
    @DecimalMin(value = "0.00", message = "sale price cannot be negative")
    private BigDecimal salePrice;

    @NotNull(message = "market price cannot be null")
    @DecimalMin(value = "0.00", message = "market price cannot be negative")
    private BigDecimal marketPrice;

    @Size(max = 255, message = "attr text length cannot exceed 255")
    private String attrText;

    @NotNull(message = "total stock cannot be null")
    @Min(value = 0, message = "total stock cannot be negative")
    @Max(value = 999999999, message = "total stock is too large")
    private Integer totalStock;

    @NotNull(message = "default sku flag cannot be null")
    private Boolean defaultSku;

    @NotNull(message = "status cannot be null")
    @Min(value = 0, message = "status must be 0 or 1")
    @Max(value = 1, message = "status must be 0 or 1")
    private Integer status;
}
