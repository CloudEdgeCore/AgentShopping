package com.cloudedge.platform.inventory.model.vo;

import lombok.Data;

@Data
public class StockPageItemResponse {

    private Long skuId;
    private String spuName;
    private String skuName;
    private Integer stock;
    private Integer totalStock;
    private Integer availableStock;
    private Integer lockedStock;
    private Integer status;
}
