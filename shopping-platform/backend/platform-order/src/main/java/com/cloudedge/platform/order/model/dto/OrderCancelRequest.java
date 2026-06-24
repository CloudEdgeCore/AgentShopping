package com.cloudedge.platform.order.model.dto;

import jakarta.validation.constraints.Size;

public class OrderCancelRequest {

    @Size(max = 255, message = "cancel reason length cannot exceed 255")
    private String cancelReason;

    public String getCancelReason() {
        return cancelReason;
    }

    public void setCancelReason(String cancelReason) {
        this.cancelReason = cancelReason;
    }
}
