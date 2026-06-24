package com.cloudedge.platform.search.service;

import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.SortOptions;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingSkuDiscountDTO;
import com.cloudedge.platform.infrastructure.marketing.service.MarketingReadService;
import com.cloudedge.platform.product.entity.CategoryDO;
import com.cloudedge.platform.product.entity.ProductSkuDO;
import com.cloudedge.platform.product.enums.ProductDataStatusEnum;
import com.cloudedge.platform.product.mapper.CategoryMapper;
import com.cloudedge.platform.product.mapper.ProductSkuMapper;
import com.cloudedge.platform.product.model.vo.PageResponse;
import com.cloudedge.platform.product.model.vo.ProductPageItemResponse;
import com.cloudedge.platform.search.model.document.ProductSearchDocument;
import com.cloudedge.platform.search.model.dto.ProductSearchPageQueryRequest;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.elasticsearch.client.elc.NativeQuery;
import org.springframework.data.elasticsearch.client.elc.NativeQueryBuilder;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.SearchHit;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
@ConditionalOnProperty(prefix = "platform.search", name = "enabled", havingValue = "true")
public class ProductSearchQueryService {

    private final ElasticsearchOperations elasticsearchOperations;
    private final ProductSkuMapper productSkuMapper;
    private final CategoryMapper categoryMapper;
    private final ObjectProvider<MarketingReadService> marketingReadServiceProvider;

    public ProductSearchQueryService(ElasticsearchOperations elasticsearchOperations,
                                     ProductSkuMapper productSkuMapper,
                                     CategoryMapper categoryMapper,
                                     ObjectProvider<MarketingReadService> marketingReadServiceProvider) {
        this.elasticsearchOperations = elasticsearchOperations;
        this.productSkuMapper = productSkuMapper;
        this.categoryMapper = categoryMapper;
        this.marketingReadServiceProvider = marketingReadServiceProvider;
    }

    public PageResponse<ProductPageItemResponse> pagePublishedProducts(ProductSearchPageQueryRequest request) {
        String keyword = trimToNull(request.getKeyword());
        NativeQueryBuilder queryBuilder = NativeQuery.builder()
                .withPageable(PageRequest.of((int) request.getCurrent() - 1, (int) request.getSize()));

        List<Query> filterList = new ArrayList<>();
        filterList.add(Query.of(q -> q.term(t -> t.field("publishStatus").value(FieldValue.of(1)))));

        List<Long> categoryIds = resolveCategoryFilterIds(request.getCategoryId());
        if (!categoryIds.isEmpty()) {
            if (categoryIds.size() == 1) {
                filterList.add(Query.of(q -> q.term(t -> t.field("categoryId").value(FieldValue.of(categoryIds.get(0))))));
            } else {
                filterList.add(Query.of(q -> q.terms(t -> t
                        .field("categoryId")
                        .terms(values -> values.value(categoryIds.stream().map(FieldValue::of).toList())))));
            }
        }
        if (request.getBrandId() != null) {
            filterList.add(Query.of(q -> q.term(t -> t.field("brandId").value(FieldValue.of(request.getBrandId())))));
        }

        List<Query> mustList = new ArrayList<>();
        if (keyword != null) {
            mustList.add(Query.of(q -> q.multiMatch(m -> m
                    .query(keyword)
                    .fields("spuName^3", "subtitle^2", "categoryName", "brandName"))));
        }

        Query rootQuery = Query.of(q -> q.bool(b -> {
            if (!mustList.isEmpty()) {
                b.must(mustList);
            }
            if (!filterList.isEmpty()) {
                b.filter(filterList);
            }
            return b;
        }));

        queryBuilder.withQuery(rootQuery);
        if (keyword != null) {
            queryBuilder.withSort(SortOptions.of(s -> s.score(sc -> sc.order(SortOrder.Desc))));
        }
        queryBuilder.withSort(SortOptions.of(s -> s.field(f -> f.field("sort").order(SortOrder.Asc))));
        queryBuilder.withSort(SortOptions.of(s -> s.field(f -> f.field("updateTime").order(SortOrder.Desc))));

        NativeQuery nativeQuery = queryBuilder.build();
        SearchHits<ProductSearchDocument> searchHits = elasticsearchOperations.search(nativeQuery, ProductSearchDocument.class);
        List<ProductSearchDocument> documents = searchHits.getSearchHits().stream()
                .map(SearchHit::getContent)
                .toList();

        Map<Long, List<ProductSkuDO>> skuMap = listEnabledSkuMap(documents);
        Map<Long, MarketingSkuDiscountDTO> discountMap = listDiscountMap(skuMap);

        List<ProductPageItemResponse> records = documents.stream()
                .map(document -> toPageItem(document, skuMap.getOrDefault(document.getSpuId(), Collections.emptyList()), discountMap))
                .toList();

        return PageResponse.<ProductPageItemResponse>builder()
                .current(request.getCurrent())
                .size(request.getSize())
                .total(searchHits.getTotalHits())
                .records(records)
                .build();
    }

    private ProductPageItemResponse toPageItem(ProductSearchDocument document,
                                               List<ProductSkuDO> skuList,
                                               Map<Long, MarketingSkuDiscountDTO> discountMap) {
        PriceRange promotionRange = buildPromotionPriceRange(skuList, discountMap);
        return ProductPageItemResponse.builder()
                .spuId(document.getSpuId())
                .spuName(document.getSpuName())
                .subtitle(document.getSubtitle())
                .coverImage(document.getCoverImage())
                .categoryId(document.getCategoryId())
                .categoryName(document.getCategoryName())
                .brandId(document.getBrandId())
                .brandName(document.getBrandName())
                .minSalePrice(document.getMinSalePrice())
                .maxSalePrice(document.getMaxSalePrice())
                .minPromotionPrice(promotionRange.minPrice())
                .maxPromotionPrice(promotionRange.maxPrice())
                .build();
    }

    private Map<Long, List<ProductSkuDO>> listEnabledSkuMap(List<ProductSearchDocument> documents) {
        if (documents == null || documents.isEmpty()) {
            return Collections.emptyMap();
        }

        List<Long> spuIds = documents.stream()
                .map(ProductSearchDocument::getSpuId)
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        if (spuIds.isEmpty()) {
            return Collections.emptyMap();
        }

        return productSkuMapper.selectList(Wrappers.<ProductSkuDO>lambdaQuery()
                        .in(ProductSkuDO::getSpuId, spuIds)
                        .eq(ProductSkuDO::getStatus, ProductDataStatusEnum.ENABLED.getCode())
                        .orderByAsc(ProductSkuDO::getId))
                .stream()
                .collect(Collectors.groupingBy(ProductSkuDO::getSpuId));
    }

    private Map<Long, MarketingSkuDiscountDTO> listDiscountMap(Map<Long, List<ProductSkuDO>> skuMap) {
        MarketingReadService marketingReadService = marketingReadServiceProvider.getIfAvailable();
        if (marketingReadService == null || skuMap == null || skuMap.isEmpty()) {
            return Collections.emptyMap();
        }

        List<Long> skuIds = skuMap.values().stream()
                .flatMap(List::stream)
                .map(ProductSkuDO::getId)
                .distinct()
                .toList();
        if (skuIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return marketingReadService.getActiveDiscountMap(skuIds);
    }

    private PriceRange buildPromotionPriceRange(List<ProductSkuDO> skuList, Map<Long, MarketingSkuDiscountDTO> discountMap) {
        if (skuList == null || skuList.isEmpty() || discountMap == null || discountMap.isEmpty()) {
            return new PriceRange(null, null);
        }

        List<BigDecimal> prices = skuList.stream()
                .map(sku -> toPromotionPrice(sku, discountMap.get(sku.getId())))
                .filter(Objects::nonNull)
                .toList();
        if (prices.isEmpty()) {
            return new PriceRange(null, null);
        }

        return new PriceRange(
                prices.stream().min(BigDecimal::compareTo).orElse(null),
                prices.stream().max(BigDecimal::compareTo).orElse(null)
        );
    }

    private BigDecimal toPromotionPrice(ProductSkuDO skuDO, MarketingSkuDiscountDTO discountDTO) {
        if (skuDO == null || discountDTO == null || discountDTO.getDiscountPrice() == null) {
            return null;
        }
        BigDecimal salePrice = skuDO.getSalePrice();
        BigDecimal discountPrice = discountDTO.getDiscountPrice();
        if (salePrice == null || discountPrice.compareTo(salePrice) >= 0) {
            return null;
        }
        return discountPrice;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private List<Long> resolveCategoryFilterIds(Long categoryId) {
        if (categoryId == null) {
            return Collections.emptyList();
        }

        List<CategoryDO> categoryList = categoryMapper.selectList(Wrappers.<CategoryDO>lambdaQuery()
                .select(CategoryDO::getId, CategoryDO::getParentId)
                .eq(CategoryDO::getStatus, ProductDataStatusEnum.ENABLED.getCode()));
        if (categoryList.isEmpty()) {
            return List.of(categoryId);
        }

        Map<Long, List<Long>> childrenMap = categoryList.stream()
                .collect(Collectors.groupingBy(
                        item -> item.getParentId() == null ? 0L : item.getParentId(),
                        Collectors.mapping(CategoryDO::getId, Collectors.toList())
                ));

        LinkedHashSet<Long> resolvedIds = new LinkedHashSet<>();
        ArrayDeque<Long> queue = new ArrayDeque<>();
        queue.offer(categoryId);

        while (!queue.isEmpty()) {
            Long currentId = queue.poll();
            if (currentId == null || !resolvedIds.add(currentId)) {
                continue;
            }
            List<Long> children = childrenMap.get(currentId);
            if (children == null || children.isEmpty()) {
                continue;
            }
            children.forEach(queue::offer);
        }

        return new ArrayList<>(resolvedIds);
    }

    private record PriceRange(BigDecimal minPrice, BigDecimal maxPrice) {
    }
}
