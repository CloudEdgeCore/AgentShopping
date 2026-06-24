package com.cloudedge.platform.inventory.service;

import com.cloudedge.platform.inventory.model.dto.StockCreateRequest;
import com.cloudedge.platform.inventory.model.dto.StockPageQueryRequest;
import com.cloudedge.platform.inventory.model.dto.StockUpdateRequest;
import com.cloudedge.platform.inventory.model.vo.PageResponse;
import com.cloudedge.platform.inventory.model.vo.StockPageItemResponse;
import com.cloudedge.platform.inventory.model.vo.StockResponse;
import jakarta.validation.Valid;

public interface InventoryAdminService {
    StockResponse createStock(@Valid StockCreateRequest request);

    StockResponse updateStock(Long skuId, @Valid StockUpdateRequest request);

    StockResponse getStock(Long skuId);

    PageResponse<StockPageItemResponse> pageStocks(@Valid StockPageQueryRequest request);
}
