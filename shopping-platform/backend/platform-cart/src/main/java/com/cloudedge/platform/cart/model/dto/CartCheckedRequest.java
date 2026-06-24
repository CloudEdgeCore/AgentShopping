package com.cloudedge.platform.cart.model.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CartCheckedRequest {
    @NotNull(message = "checked cannot be null")
    private Boolean checked;
}
