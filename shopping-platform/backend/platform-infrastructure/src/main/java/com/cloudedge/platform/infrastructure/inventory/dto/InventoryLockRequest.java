package com.cloudedge.platform.infrastructure.inventory.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class InventoryLockRequest {

    private String orderNo;
    private String bizType;
    private List<InventoryLockItemDTO> items;
}
