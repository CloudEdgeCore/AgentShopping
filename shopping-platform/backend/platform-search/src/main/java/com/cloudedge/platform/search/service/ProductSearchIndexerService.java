package com.cloudedge.platform.search.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.cloudedge.platform.product.entity.BrandDO;
import com.cloudedge.platform.product.entity.CategoryDO;
import com.cloudedge.platform.product.entity.ProductSkuDO;
import com.cloudedge.platform.product.entity.ProductSpuDO;
import com.cloudedge.platform.product.enums.ProductDataStatusEnum;
import com.cloudedge.platform.product.mapper.BrandMapper;
import com.cloudedge.platform.product.mapper.CategoryMapper;
import com.cloudedge.platform.product.mapper.ProductSkuMapper;
import com.cloudedge.platform.product.mapper.ProductSpuMapper;
import com.cloudedge.platform.search.model.document.ProductSearchDocument;
import jakarta.annotation.PostConstruct;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.IndexOperations;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@ConditionalOnProperty(prefix = "platform.search", name = "enabled", havingValue = "true")
public class ProductSearchIndexerService {

    private final ProductSpuMapper productSpuMapper;
    private final ProductSkuMapper productSkuMapper;
    private final CategoryMapper categoryMapper;
    private final BrandMapper brandMapper;
    private final ElasticsearchOperations elasticsearchOperations;

    public ProductSearchIndexerService(ProductSpuMapper productSpuMapper,
                                       ProductSkuMapper productSkuMapper,
                                       CategoryMapper categoryMapper,
                                       BrandMapper brandMapper,
                                       ElasticsearchOperations elasticsearchOperations) {
        this.productSpuMapper = productSpuMapper;
        this.productSkuMapper = productSkuMapper;
        this.categoryMapper = categoryMapper;
        this.brandMapper = brandMapper;
        this.elasticsearchOperations = elasticsearchOperations;
    }

    @PostConstruct
    public void ensureIndex() {
        IndexOperations indexOperations = elasticsearchOperations.indexOps(ProductSearchDocument.class);
        if (!indexOperations.exists()) {
            indexOperations.create();
            indexOperations.putMapping(indexOperations.createMapping(ProductSearchDocument.class));
        }
    }

    public void rebuildAll() {
        IndexOperations indexOperations = elasticsearchOperations.indexOps(ProductSearchDocument.class);
        if (indexOperations.exists()) {
            indexOperations.delete();
        }
        indexOperations.create();
        indexOperations.putMapping(indexOperations.createMapping(ProductSearchDocument.class));

        long current = 1L;
        long size = 500L;
        while (true) {
            Page<ProductSpuDO> page = productSpuMapper.selectPage(
                    new Page<>(current, size),
                    Wrappers.<ProductSpuDO>lambdaQuery().orderByAsc(ProductSpuDO::getId)
            );
            if (page.getRecords().isEmpty()) {
                break;
            }
            saveBatch(page.getRecords());
            if (current * size >= page.getTotal()) {
                break;
            }
            current++;
        }

        refreshIndex();
    }

    public void syncBySpuId(Long spuId) {
        if (spuId == null) {
            return;
        }
        ProductSpuDO spuDO = productSpuMapper.selectById(spuId);
        if (spuDO == null) {
            deleteBySpuId(spuId);
            return;
        }
        retryOnFailure(() -> {
            saveBatch(List.of(spuDO));
            refreshIndex();
        });
    }

    public void deleteBySpuId(Long spuId) {
        if (spuId == null) {
            return;
        }
        retryOnFailure(() -> {
            elasticsearchOperations.delete(String.valueOf(spuId), ProductSearchDocument.class);
            refreshIndex();
        });
    }

    private void retryOnFailure(Runnable action) {
        RuntimeException lastError = null;
        for (int attempt = 1; attempt <= 3; attempt++) {
            try {
                action.run();
                return;
            } catch (RuntimeException ex) {
                lastError = ex;
                if (attempt < 3) {
                    try {
                        Thread.sleep(500L * attempt);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }
        throw new RuntimeException("ES sync failed after 3 attempts", lastError);
    }

    private void saveBatch(List<ProductSpuDO> spuList) {
        if (spuList == null || spuList.isEmpty()) {
            return;
        }

        List<Long> spuIds = spuList.stream().map(ProductSpuDO::getId).toList();
        Map<Long, List<ProductSkuDO>> skuMap = productSkuMapper.selectList(
                        Wrappers.<ProductSkuDO>lambdaQuery()
                                .in(ProductSkuDO::getSpuId, spuIds)
                                .eq(ProductSkuDO::getStatus, ProductDataStatusEnum.ENABLED.getCode())
                                .orderByAsc(ProductSkuDO::getId))
                .stream()
                .collect(Collectors.groupingBy(ProductSkuDO::getSpuId));

        Map<Long, CategoryDO> categoryMap = loadCategoryMap(
                spuList.stream().map(ProductSpuDO::getCategoryId).filter(Objects::nonNull).distinct().toList()
        );
        Map<Long, BrandDO> brandMap = loadBrandMap(
                spuList.stream().map(ProductSpuDO::getBrandId).filter(Objects::nonNull).distinct().toList()
        );

        List<ProductSearchDocument> documents = spuList.stream()
                .map(spu -> {
                    List<ProductSkuDO> skuList = skuMap.getOrDefault(spu.getId(), Collections.emptyList());
                    PriceRange priceRange = buildPriceRange(skuList);
                    CategoryDO categoryDO = categoryMap.get(spu.getCategoryId());
                    BrandDO brandDO = brandMap.get(spu.getBrandId());

                    return ProductSearchDocument.builder()
                            .spuId(spu.getId())
                            .spuName(spu.getSpuName())
                            .subtitle(spu.getSubtitle())
                            .coverImage(spu.getCoverImage())
                            .categoryId(spu.getCategoryId())
                            .categoryName(categoryDO == null ? null : categoryDO.getName())
                            .brandId(spu.getBrandId())
                            .brandName(brandDO == null ? null : brandDO.getName())
                            .minSalePrice(priceRange.minPrice())
                            .maxSalePrice(priceRange.maxPrice())
                            .publishStatus(spu.getPublishStatus())
                            .sort(spu.getSort())
                            .updateTime(spu.getUpdateTime() == null ? null : spu.getUpdateTime().toLocalDate())
                            .build();
                })
                .toList();

        elasticsearchOperations.save(documents);
    }

    private Map<Long, CategoryDO> loadCategoryMap(List<Long> categoryIds) {
        if (categoryIds == null || categoryIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return categoryMapper.selectBatchIds(categoryIds).stream()
                .collect(Collectors.toMap(CategoryDO::getId, Function.identity()));
    }

    private Map<Long, BrandDO> loadBrandMap(List<Long> brandIds) {
        if (brandIds == null || brandIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return brandMapper.selectBatchIds(brandIds).stream()
                .collect(Collectors.toMap(BrandDO::getId, Function.identity()));
    }

    private PriceRange buildPriceRange(List<ProductSkuDO> skuList) {
        if (skuList == null || skuList.isEmpty()) {
            return new PriceRange(null, null);
        }

        BigDecimal minPrice = skuList.stream()
                .map(ProductSkuDO::getSalePrice)
                .filter(Objects::nonNull)
                .min(BigDecimal::compareTo)
                .orElse(null);

        BigDecimal maxPrice = skuList.stream()
                .map(ProductSkuDO::getSalePrice)
                .filter(Objects::nonNull)
                .max(BigDecimal::compareTo)
                .orElse(null);

        return new PriceRange(minPrice, maxPrice);
    }

    private void refreshIndex() {
        elasticsearchOperations.indexOps(ProductSearchDocument.class).refresh();
    }

    private record PriceRange(BigDecimal minPrice, BigDecimal maxPrice) {
    }
}
