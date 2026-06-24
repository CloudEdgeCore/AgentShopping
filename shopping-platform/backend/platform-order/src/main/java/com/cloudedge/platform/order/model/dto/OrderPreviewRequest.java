package com.cloudedge.platform.order.model.dto;

import jakarta.validation.Valid;
import lombok.Data;

import java.util.List;

@Data
public class OrderPreviewRequest {

    @Valid
    private List<OrderSubmitItemRequest> items;

    private List<Long> cartItemIds;

    private Long userCouponId;
}
