package com.cloudedge.platform.inventory.model.vo;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class StockResponse {

    private Long skuId;
    private Integer totalStock;
    private Integer availableStock;
    private Integer lockedStock;
    private Integer status;
}
