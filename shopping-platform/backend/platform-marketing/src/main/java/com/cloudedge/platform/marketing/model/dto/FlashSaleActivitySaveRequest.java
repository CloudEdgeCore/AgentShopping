package com.cloudedge.platform.marketing.model.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class FlashSaleActivitySaveRequest {

    @NotBlank(message = "name cannot be blank")
    @Size(max = 64, message = "name length cannot exceed 64")
    private String name;

    @NotNull(message = "startTime cannot be null")
    private LocalDateTime startTime;

    @NotNull(message = "endTime cannot be null")
    private LocalDateTime endTime;

    @NotNull(message = "status cannot be null")
    private Integer status;

    @Valid
    @NotEmpty(message = "items cannot be empty")
    private List<FlashSaleSkuSaveRequest> items;
}
