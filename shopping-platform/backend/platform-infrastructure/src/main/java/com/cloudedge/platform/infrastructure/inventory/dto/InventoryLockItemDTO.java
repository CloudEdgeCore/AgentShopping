package com.cloudedge.platform.infrastructure.inventory.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class InventoryLockItemDTO {
    private Long skuId;
    private Integer quantity;
}
