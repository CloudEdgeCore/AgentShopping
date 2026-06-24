package com.cloudedge.platform.infrastructure.product.service;

import com.cloudedge.platform.infrastructure.product.dto.ProductCartSkuInfo;

import java.util.List;
import java.util.Map;

public interface ProductCartReadService {

    ProductCartSkuInfo getSaleableSkuInfoBySkuId(Long skuId);

    Map<Long, ProductCartSkuInfo> getSaleableSkuInfoMap(List<Long> skuIds);
}
