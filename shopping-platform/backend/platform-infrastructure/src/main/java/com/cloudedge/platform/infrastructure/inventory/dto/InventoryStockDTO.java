package com.cloudedge.platform.infrastructure.inventory.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class InventoryStockDTO {
    private Long skuId;
    private Integer totalStock;
    private Integer availableStock;
    private Integer lockedStock;
    private Integer status;
}
