package com.cloudedge.platform.product.model.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

@Data
public class ProductSaveRequest {

    @NotNull(message = "categoryId cannot be null")
    private Long categoryId;

    @NotNull(message = "brandId cannot be null")
    private Long brandId;

    @NotBlank(message = "spu name cannot be blank")
    @Size(max = 128, message = "spu name length cannot exceed 128")
    private String spuName;

    @Size(max = 255, message = "subtitle length cannot exceed 255")
    private String subtitle;

    @Size(max = 255, message = "cover image length cannot exceed 255")
    private String coverImage;

    private List<@Size(max = 255, message = "album image length cannot exceed 255") String> albumImages;

    @Size(max = 5000, message = "detail length cannot exceed 5000")
    private String detail;

    @NotNull(message = "sort cannot be null")
    @Min(value = 0, message = "sort cannot be negative")
    @Max(value = 999999, message = "sort is too large")
    private Integer sort;

    @Valid
    @NotEmpty(message = "sku list cannot be empty")
    private List<ProductSkuSaveRequest> skuList;
}
