package com.cloudedge.platform.infrastructure.inventory.service;

import com.cloudedge.platform.infrastructure.inventory.dto.InventoryStockDTO;

import java.util.List;
import java.util.Map;

public interface InventoryReadService {

    InventoryStockDTO getStockBySkuId(Long skuId);

    Map<Long, InventoryStockDTO> getStockMap(List<Long> skuIds);
}
