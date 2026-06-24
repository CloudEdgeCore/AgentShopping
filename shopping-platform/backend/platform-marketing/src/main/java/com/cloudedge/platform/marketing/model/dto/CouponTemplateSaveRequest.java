package com.cloudedge.platform.marketing.model.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class CouponTemplateSaveRequest {

    @NotBlank(message = "name cannot be blank")
    @Size(max = 64, message = "name length cannot exceed 64")
    private String name;

    @NotNull(message = "couponType cannot be null")
    private Integer couponType;

    @NotNull(message = "thresholdAmount cannot be null")
    @DecimalMin(value = "0.00", message = "thresholdAmount cannot be negative")
    private BigDecimal thresholdAmount;

    @NotNull(message = "discountAmount cannot be null")
    @DecimalMin(value = "0.00", message = "discountAmount cannot be negative")
    private BigDecimal discountAmount;

    @DecimalMin(value = "0.00", message = "discountRate cannot be negative")
    @DecimalMax(value = "10.00", message = "discountRate cannot exceed 10")
    private BigDecimal discountRate;

    @NotNull(message = "totalCount cannot be null")
    @Min(value = 1, message = "totalCount must be greater than 0")
    @Max(value = 9999999, message = "totalCount is too large")
    private Integer totalCount;

    @NotNull(message = "perUserLimit cannot be null")
    @Min(value = 1, message = "perUserLimit must be greater than 0")
    @Max(value = 100, message = "perUserLimit is too large")
    private Integer perUserLimit;

    @NotNull(message = "scopeType cannot be null")
    private Integer scopeType;

    private List<Long> scopeIds;

    @NotNull(message = "receiveStartTime cannot be null")
    private LocalDateTime receiveStartTime;

    @NotNull(message = "receiveEndTime cannot be null")
    private LocalDateTime receiveEndTime;

    @NotNull(message = "validFrom cannot be null")
    private LocalDateTime validFrom;

    @NotNull(message = "validTo cannot be null")
    private LocalDateTime validTo;

    @Size(max = 500, message = "description length cannot exceed 500")
    private String description;

    @NotNull(message = "status cannot be null")
    private Integer status;
}
