package com.cloudedge.platform.infrastructure.inventory.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class InventoryStockSaveDTO {

    private Long skuId;
    private Integer totalStock;
    private Integer status;
}
