package com.cloudedge.platform.search.service.impl;

import com.cloudedge.platform.infrastructure.product.service.ProductSearchSyncService;
import com.cloudedge.platform.search.service.ProductSearchIndexerService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

@Service
@ConditionalOnProperty(prefix = "platform.search", name = "enabled", havingValue = "true")
public class ProductSearchSyncServiceImpl implements ProductSearchSyncService {

    private final ProductSearchIndexerService productSearchIndexerService;

    public ProductSearchSyncServiceImpl(ProductSearchIndexerService productSearchIndexerService) {
        this.productSearchIndexerService = productSearchIndexerService;
    }

    @Override
    public void syncBySpuId(Long spuId) {
        productSearchIndexerService.syncBySpuId(spuId);
    }

    @Override
    public void deleteBySpuId(Long spuId) {
        productSearchIndexerService.deleteBySpuId(spuId);
    }
}
