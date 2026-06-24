package com.cloudedge.platform.payment.model.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class PaymentCreateRequest {

    @NotBlank(message = "orderNo cannot be blank")
    private String orderNo;
}
