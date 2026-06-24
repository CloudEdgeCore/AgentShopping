package com.cloudedge.platform.inventory.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryStockDTO;
import com.cloudedge.platform.infrastructure.inventory.service.InventoryReadService;
import com.cloudedge.platform.inventory.entity.SkuStockDO;
import com.cloudedge.platform.inventory.mapper.SkuStockMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class InventoryReadServiceImpl implements InventoryReadService {

    @Autowired
    private SkuStockMapper skuStockMapper;

    @Override
    public InventoryStockDTO getStockBySkuId(Long skuId) {
        return getStockMap(List.of(skuId)).get(skuId);
    }

    @Override
    public Map<Long, InventoryStockDTO> getStockMap(List<Long> skuIds) {
        if (skuIds == null || skuIds.isEmpty()) {
            return Collections.emptyMap();
        }

        return skuStockMapper.selectList(Wrappers.<SkuStockDO>lambdaQuery()
                        .in(SkuStockDO::getSkuId, skuIds))
                .stream()
                .collect(Collectors.toMap(SkuStockDO::getSkuId, this::buildDto, (a, b) -> a));
    }

    private InventoryStockDTO buildDto(SkuStockDO stockDO) {
        return InventoryStockDTO.builder()
                .skuId(stockDO.getSkuId())
                .totalStock(stockDO.getTotalStock())
                .availableStock(stockDO.getAvailableStock())
                .lockedStock(stockDO.getLockedStock())
                .status(stockDO.getStatus())
                .build();
    }
}
