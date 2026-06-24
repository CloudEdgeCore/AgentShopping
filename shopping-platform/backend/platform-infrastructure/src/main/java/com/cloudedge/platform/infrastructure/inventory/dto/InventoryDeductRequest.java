package com.cloudedge.platform.infrastructure.inventory.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class InventoryDeductRequest {

    private String orderNo;
    private String bizType;
}
