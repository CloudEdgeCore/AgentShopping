package com.cloudedge.platform.inventory.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.inventory.entity.SkuStockDO;
import com.cloudedge.platform.inventory.exception.InventoryErrorCode;
import com.cloudedge.platform.inventory.mapper.SkuStockMapper;
import com.cloudedge.platform.inventory.model.dto.StockCreateRequest;
import com.cloudedge.platform.inventory.model.dto.StockPageQueryRequest;
import com.cloudedge.platform.inventory.model.dto.StockUpdateRequest;
import com.cloudedge.platform.inventory.model.vo.PageResponse;
import com.cloudedge.platform.inventory.model.vo.StockPageItemResponse;
import com.cloudedge.platform.inventory.model.vo.StockResponse;
import com.cloudedge.platform.inventory.service.InventoryAdminService;
import com.cloudedge.platform.inventory.support.InventoryAdminSupport;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class InventoryAdminServiceImpl implements InventoryAdminService {

    @Autowired
    private SkuStockMapper skuStockMapper;

    @Autowired
    private InventoryAdminSupport inventoryAdminSupport;

    @Override
    public StockResponse createStock(StockCreateRequest request) {
        inventoryAdminSupport.requireAdminUser();

        SkuStockDO existing = skuStockMapper.selectOne(Wrappers.<SkuStockDO>lambdaQuery()
                .eq(SkuStockDO::getSkuId, request.getSkuId())
                .last("limit 1"));
        if (existing != null) {
            throw new BizException(InventoryErrorCode.STOCK_ALREADY_EXISTS);
        }

        SkuStockDO stockDO = new SkuStockDO();
        stockDO.setSkuId(request.getSkuId());
        stockDO.setTotalStock(request.getTotalStock());
        stockDO.setAvailableStock(request.getTotalStock());
        stockDO.setLockedStock(0);
        stockDO.setStatus(request.getStatus());
        stockDO.setDeleted(0);

        skuStockMapper.insert(stockDO);
        return buildResponse(stockDO);
    }

    @Override
    public StockResponse updateStock(Long skuId, StockUpdateRequest request) {
        inventoryAdminSupport.requireAdminUser();

        SkuStockDO stockDO = getStockOrThrow(skuId);
        if (request.getTotalStock() < stockDO.getLockedStock()) {
            throw new BizException(InventoryErrorCode.INVALID_TOTAL_STOCK);
        }

        stockDO.setTotalStock(request.getTotalStock());
        stockDO.setAvailableStock(request.getTotalStock() - stockDO.getLockedStock());
        stockDO.setStatus(request.getStatus());

        skuStockMapper.updateById(stockDO);
        return buildResponse(stockDO);
    }

    @Override
    public StockResponse getStock(Long skuId) {
        inventoryAdminSupport.requireAdminUser();
        return buildResponse(getStockOrThrow(skuId));
    }

    @Override
    public PageResponse<StockPageItemResponse> pageStocks(StockPageQueryRequest request) {
        inventoryAdminSupport.requireAdminUser();

        Page<StockPageItemResponse> page = new Page<>(request.getCurrent(), request.getSize());
        var resultPage = skuStockMapper.selectAdminStockPage(page, trimToNull(request.getKeyword()));

        return PageResponse.<StockPageItemResponse>builder()
                .current(resultPage.getCurrent())
                .size(resultPage.getSize())
                .total(resultPage.getTotal())
                .records(resultPage.getRecords())
                .build();
    }

    private SkuStockDO getStockOrThrow(Long skuId) {
        SkuStockDO stockDO = skuStockMapper.selectOne(Wrappers.<SkuStockDO>lambdaQuery()
                .eq(SkuStockDO::getSkuId, skuId)
                .last("limit 1"));

        if (stockDO == null) {
            throw new BizException(InventoryErrorCode.STOCK_NOT_FOUND);
        }
        return stockDO;
    }

    private StockResponse buildResponse(SkuStockDO stockDO) {
        return StockResponse.builder()
                .skuId(stockDO.getSkuId())
                .totalStock(stockDO.getTotalStock())
                .availableStock(stockDO.getAvailableStock())
                .lockedStock(stockDO.getLockedStock())
                .status(stockDO.getStatus())
                .build();
    }

    private String trimToNull(String keyword) {
        if (keyword == null) {
            return null;
        }
        String trimmed = keyword.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
