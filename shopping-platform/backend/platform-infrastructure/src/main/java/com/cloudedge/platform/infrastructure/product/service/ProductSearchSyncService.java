package com.cloudedge.platform.infrastructure.product.service;

public interface ProductSearchSyncService {

    void syncBySpuId(Long spuId);

    void deleteBySpuId(Long spuId);
}
