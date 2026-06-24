package com.cloudedge.platform.product.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.infrastructure.product.dto.ProductCartSkuInfo;
import com.cloudedge.platform.infrastructure.product.service.ProductCartReadService;
import com.cloudedge.platform.product.entity.ProductSkuDO;
import com.cloudedge.platform.product.entity.ProductSpuDO;
import com.cloudedge.platform.product.enums.ProductDataStatusEnum;
import com.cloudedge.platform.product.enums.ProductPublishStatusEnum;
import com.cloudedge.platform.product.mapper.ProductSkuMapper;
import com.cloudedge.platform.product.mapper.ProductSpuMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class ProductCartReadServiceImpl implements ProductCartReadService {

    @Autowired
    private ProductSkuMapper productSkuMapper;
    @Autowired
    private ProductSpuMapper productSpuMapper;

    /**
     * 只有当sku启用并且spu已经发布，才会把改商品返回给购物车
     * @param skuId Long
     * @return ProductCartSkuInfo
     */
    @Override
    public ProductCartSkuInfo getSaleableSkuInfoBySkuId(Long skuId) {
        return getSaleableSkuInfoMap(List.of(skuId)).get(skuId);
    }

    public Map<Long, ProductCartSkuInfo> getSaleableSkuInfoMap(List<Long> skuIds) {
        if (skuIds == null || skuIds.isEmpty()) return Collections.emptyMap();

        List<ProductSkuDO> skuList = productSkuMapper.selectList(Wrappers.<ProductSkuDO>lambdaQuery()
                .in(ProductSkuDO::getId, skuIds)
                .eq(ProductSkuDO::getStatus, ProductDataStatusEnum.ENABLED.getCode()));

        if (skuList.isEmpty()) return Collections.emptyMap();

        List<Long> spuIds = skuList.stream().map(ProductSkuDO::getSpuId).filter(Objects::nonNull).distinct().toList();

        Map<Long, ProductSpuDO> spuMap = productSpuMapper.selectBatchIds(spuIds).stream()
                .filter(spu -> ProductPublishStatusEnum.PUBLISHED.getCode().equals(spu.getPublishStatus()))
                .collect(Collectors.toMap(ProductSpuDO::getId, Function.identity()));

        return skuList.stream()
                .filter(sku -> spuMap.containsKey(sku.getSpuId()))
                .collect(Collectors.toMap(ProductSkuDO::getId, sku -> {
                    ProductSpuDO spu = spuMap.get(sku.getSpuId());

                    return ProductCartSkuInfo.builder()
                            .skuId(sku.getId())
                            .spuId(spu.getId())
                            .categoryId(spu.getCategoryId())
                            .spuName(spu.getSpuName())
                            .skuName(sku.getSkuName())
                            .skuImage(sku.getImageUrl())
                            .skuAttrText(sku.getAttrText())
                            .salePrice(sku.getSalePrice())
                            .build();
                }));
    }
}
