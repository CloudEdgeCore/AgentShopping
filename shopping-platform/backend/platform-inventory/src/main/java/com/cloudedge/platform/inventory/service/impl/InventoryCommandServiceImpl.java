package com.cloudedge.platform.inventory.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryDeductRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryLockItemDTO;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryLockRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryReleaseRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryStockSaveDTO;
import com.cloudedge.platform.infrastructure.inventory.service.InventoryCommandService;
import com.cloudedge.platform.inventory.entity.StockLockRecordDO;
import com.cloudedge.platform.inventory.entity.SkuStockDO;
import com.cloudedge.platform.inventory.enums.InventoryStatusEnum;
import com.cloudedge.platform.inventory.enums.StockLockStatusEnum;
import com.cloudedge.platform.inventory.exception.InventoryErrorCode;
import com.cloudedge.platform.inventory.mapper.StockLockRecordMapper;
import com.cloudedge.platform.inventory.mapper.SkuStockMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Service
public class InventoryCommandServiceImpl implements InventoryCommandService {

    @Autowired
    private SkuStockMapper skuStockMapper;

    @Autowired
    private StockLockRecordMapper stockLockRecordMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void lock(InventoryLockRequest request) {
        List<InventoryLockItemDTO> items = request == null ? Collections.emptyList() : request.getItems();
        if (items == null || items.isEmpty()) {
            throw new BizException(InventoryErrorCode.LOCK_ITEMS_EMPTY);
        }

        for (InventoryLockItemDTO item : items) {
            if (item.getQuantity() == null || item.getQuantity() <= 0) {
                throw new BizException(InventoryErrorCode.INVALID_LOCK_QUANTITY);
            }
            lockOne(request.getOrderNo(), request.getBizType(), item.getSkuId(), item.getQuantity());
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void release(InventoryReleaseRequest request) {
        List<StockLockRecordDO> lockRecordList = listLockedRecords(request.getOrderNo(), request.getBizType());
        if (lockRecordList.isEmpty()) {
            return;
        }

        for (StockLockRecordDO record : lockRecordList) {
            int rows = skuStockMapper.update(null, Wrappers.<SkuStockDO>lambdaUpdate()
                    .eq(SkuStockDO::getSkuId, record.getSkuId())
                    .ge(SkuStockDO::getLockedStock, record.getLockQuantity())
                    .setSql("available_stock = available_stock + " + record.getLockQuantity())
                    .setSql("locked_stock = locked_stock - " + record.getLockQuantity()));
            if (rows <= 0) {
                throw new BizException(InventoryErrorCode.STOCK_OPERATION_FAILED);
            }

            StockLockRecordDO updateRecord = new StockLockRecordDO();
            updateRecord.setId(record.getId());
            updateRecord.setStatus(StockLockStatusEnum.RELEASED.getCode());
            stockLockRecordMapper.updateById(updateRecord);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deduct(InventoryDeductRequest request) {
        List<StockLockRecordDO> lockRecordList = listLockedRecords(request.getOrderNo(), request.getBizType());
        if (lockRecordList.isEmpty()) {
            return;
        }

        for (StockLockRecordDO record : lockRecordList) {
            int rows = skuStockMapper.update(null, Wrappers.<SkuStockDO>lambdaUpdate()
                    .eq(SkuStockDO::getSkuId, record.getSkuId())
                    .ge(SkuStockDO::getLockedStock, record.getLockQuantity())
                    .ge(SkuStockDO::getTotalStock, record.getLockQuantity())
                    .setSql("total_stock = total_stock - " + record.getLockQuantity())
                    .setSql("locked_stock = locked_stock - " + record.getLockQuantity()));
            if (rows <= 0) {
                throw new BizException(InventoryErrorCode.STOCK_OPERATION_FAILED);
            }

            StockLockRecordDO updateRecord = new StockLockRecordDO();
            updateRecord.setId(record.getId());
            updateRecord.setStatus(StockLockStatusEnum.DEDUCTED.getCode());
            stockLockRecordMapper.updateById(updateRecord);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void saveStocks(List<InventoryStockSaveDTO> stocks) {
        Map<Long, InventoryStockSaveDTO> stockMap = new LinkedHashMap<>();
        for (InventoryStockSaveDTO stock : stocks == null ? Collections.<InventoryStockSaveDTO>emptyList() : stocks) {
            if (stock == null || stock.getSkuId() == null) {
                continue;
            }
            stockMap.put(stock.getSkuId(), stock);
        }
        if (stockMap.isEmpty()) {
            return;
        }

        List<Long> skuIds = stockMap.keySet().stream().toList();
        Map<Long, SkuStockDO> existingStockMap = skuStockMapper.selectList(Wrappers.<SkuStockDO>lambdaQuery()
                        .in(SkuStockDO::getSkuId, skuIds))
                .stream()
                .collect(java.util.stream.Collectors.toMap(SkuStockDO::getSkuId, stock -> stock, (a, b) -> a));

        for (InventoryStockSaveDTO stock : stockMap.values()) {
            Integer totalStock = stock.getTotalStock() == null ? 0 : stock.getTotalStock();
            Integer status = stock.getStatus() == null ? InventoryStatusEnum.ENABLED.getCode() : stock.getStatus();
            SkuStockDO existingStock = existingStockMap.get(stock.getSkuId());
            if (existingStock == null) {
                SkuStockDO stockDO = new SkuStockDO();
                stockDO.setSkuId(stock.getSkuId());
                stockDO.setTotalStock(totalStock);
                stockDO.setAvailableStock(totalStock);
                stockDO.setLockedStock(0);
                stockDO.setStatus(status);
                stockDO.setDeleted(0);
                skuStockMapper.insert(stockDO);
                continue;
            }

            if (totalStock < existingStock.getLockedStock()) {
                throw new BizException(InventoryErrorCode.INVALID_TOTAL_STOCK);
            }

            existingStock.setTotalStock(totalStock);
            existingStock.setAvailableStock(totalStock - existingStock.getLockedStock());
            existingStock.setStatus(status);
            skuStockMapper.updateById(existingStock);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteStocksBySkuIds(List<Long> skuIds) {
        List<Long> validSkuIds = skuIds == null ? Collections.emptyList() : skuIds.stream()
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        if (validSkuIds.isEmpty()) {
            return;
        }

        Long lockedCount = stockLockRecordMapper.selectCount(Wrappers.<StockLockRecordDO>lambdaQuery()
                .in(StockLockRecordDO::getSkuId, validSkuIds)
                .eq(StockLockRecordDO::getStatus, StockLockStatusEnum.LOCKED.getCode()));
        if (lockedCount != null && lockedCount > 0) {
            throw new BizException(InventoryErrorCode.STOCK_HAS_LOCKED_RECORDS);
        }

        skuStockMapper.delete(Wrappers.<SkuStockDO>lambdaQuery()
                .in(SkuStockDO::getSkuId, validSkuIds));
    }

    private void lockOne(String orderNo, String bizType, Long skuId, Integer quantity) {
        StockLockRecordDO existingRecord = stockLockRecordMapper.selectOne(Wrappers.<StockLockRecordDO>lambdaQuery()
                .eq(StockLockRecordDO::getOrderNo, orderNo)
                .eq(StockLockRecordDO::getBizType, bizType)
                .eq(StockLockRecordDO::getSkuId, skuId)
                .last("limit 1"));

        // 幂等：同一订单同 SKU 已有"进行中"的锁定记录时跳过；
        // 若历史记录已释放/已扣减（RELEASED/DEDUCTED），允许重新锁定并新增锁定记录
        if (existingRecord != null && StockLockStatusEnum.LOCKED.getCode().equals(existingRecord.getStatus())) {
            return;
        }

        int rows = skuStockMapper.update(null, Wrappers.<SkuStockDO>lambdaUpdate()
                .eq(SkuStockDO::getSkuId, skuId)
                .eq(SkuStockDO::getStatus, InventoryStatusEnum.ENABLED.getCode())
                .ge(SkuStockDO::getAvailableStock, quantity)
                .setSql("available_stock = available_stock - " + quantity)
                .setSql("locked_stock = locked_stock + " + quantity));

        if (rows <= 0) {
            throw new BizException(InventoryErrorCode.STOCK_NOT_ENOUGH);
        }

        StockLockRecordDO recordDO = new StockLockRecordDO();
        recordDO.setOrderNo(orderNo);
        recordDO.setBizType(bizType);
        recordDO.setSkuId(skuId);
        recordDO.setLockQuantity(quantity);
        recordDO.setStatus(StockLockStatusEnum.LOCKED.getCode());
        recordDO.setDeleted(0);
        stockLockRecordMapper.insert(recordDO);
    }

    private List<StockLockRecordDO> listLockedRecords(String orderNo, String bizType) {
        return stockLockRecordMapper.selectList(Wrappers.<StockLockRecordDO>lambdaQuery()
                .eq(StockLockRecordDO::getOrderNo, orderNo)
                .eq(StockLockRecordDO::getBizType, bizType)
                .eq(StockLockRecordDO::getStatus, StockLockStatusEnum.LOCKED.getCode())
                .orderByAsc(StockLockRecordDO::getId));
    }
}
