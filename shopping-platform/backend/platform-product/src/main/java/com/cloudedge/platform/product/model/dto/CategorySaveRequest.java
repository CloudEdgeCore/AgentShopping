package com.cloudedge.platform.product.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class CategorySaveRequest {

    @NotNull(message = "parentId cannot be null")
    private Long parentId;

    @NotBlank(message = "category name cannot be blank")
    @Size(max = 64, message = "category name length cannot exceed 64")
    private String name;

    @Size(max = 255, message = "icon url length cannot exceed 255")
    private String iconUrl;

    @NotNull(message = "sort cannot be null")
    @Min(value = 0, message = "sort cannot be negative")
    @Max(value = 999999, message = "sort is too large")
    private Integer sort;

    @NotNull(message = "status cannot be null")
    @Min(value = 0, message = "status must be 0 or 1")
    @Max(value = 1, message = "status must be 0 or 1")
    private Integer status;
}
