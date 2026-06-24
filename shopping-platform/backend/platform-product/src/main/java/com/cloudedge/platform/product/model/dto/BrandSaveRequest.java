package com.cloudedge.platform.product.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class BrandSaveRequest {

    @NotBlank(message = "brand name cannot be blank")
    @Size(max = 64, message = "brand name length cannot exceed 64")
    private String name;

    @Size(max = 255, message = "logo url length cannot exceed 255")
    private String logoUrl;

    @Size(max = 500, message = "description length cannot exceed 500")
    private String description;

    @NotNull(message = "sort cannot be null")
    @Min(value = 0, message = "sort cannot be negative")
    @Max(value = 999999, message = "sort is too large")
    private Integer sort;

    @NotNull(message = "status cannot be null")
    @Min(value = 0, message = "status must be 0 or 1")
    @Max(value = 1, message = "status must be 0 or 1")
    private Integer status;
}
