package com.cloudedge.platform.infrastructure.inventory.service;

import com.cloudedge.platform.infrastructure.inventory.dto.InventoryDeductRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryLockRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryReleaseRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryStockSaveDTO;

import java.util.List;

public interface InventoryCommandService {

    void lock(InventoryLockRequest request);

    void release(InventoryReleaseRequest request);

    void deduct(InventoryDeductRequest request);

    void saveStocks(List<InventoryStockSaveDTO> stocks);

    void deleteStocksBySkuIds(List<Long> skuIds);
}
