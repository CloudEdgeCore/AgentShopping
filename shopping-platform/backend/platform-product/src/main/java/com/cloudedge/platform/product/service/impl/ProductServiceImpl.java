package com.cloudedge.platform.product.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.infrastructure.inventory.service.InventoryCommandService;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryStockDTO;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryStockSaveDTO;
import com.cloudedge.platform.infrastructure.inventory.service.InventoryReadService;
import com.cloudedge.platform.infrastructure.product.service.ProductSearchSyncService;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingSkuDiscountDTO;
import com.cloudedge.platform.infrastructure.marketing.service.MarketingReadService;
import com.cloudedge.platform.product.entity.BrandDO;
import com.cloudedge.platform.product.entity.CategoryDO;
import com.cloudedge.platform.product.entity.ProductSkuDO;
import com.cloudedge.platform.product.entity.ProductSpuDO;
import com.cloudedge.platform.product.enums.ProductDataStatusEnum;
import com.cloudedge.platform.product.enums.ProductPublishStatusEnum;
import com.cloudedge.platform.product.exception.ProductErrorCode;
import com.cloudedge.platform.product.mapper.BrandMapper;
import com.cloudedge.platform.product.mapper.CategoryMapper;
import com.cloudedge.platform.product.mapper.ProductSkuMapper;
import com.cloudedge.platform.product.mapper.ProductSpuMapper;
import com.cloudedge.platform.product.model.dto.AdminProductPageQueryRequest;
import com.cloudedge.platform.product.model.dto.ProductPageQueryRequest;
import com.cloudedge.platform.product.model.dto.ProductPublishRequest;
import com.cloudedge.platform.product.model.dto.ProductSaveRequest;
import com.cloudedge.platform.product.model.dto.ProductSkuSaveRequest;
import com.cloudedge.platform.product.model.vo.AdminProductDetailResponse;
import com.cloudedge.platform.product.model.vo.AdminProductPageItemResponse;
import com.cloudedge.platform.product.model.vo.PageResponse;
import com.cloudedge.platform.product.model.vo.ProductDetailResponse;
import com.cloudedge.platform.product.model.vo.ProductPageItemResponse;
import com.cloudedge.platform.product.model.vo.ProductSkuResponse;
import com.cloudedge.platform.product.service.ProductService;
import com.cloudedge.platform.product.support.ProductAdminSupport;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.math.BigDecimal;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class ProductServiceImpl implements ProductService {

    @Autowired
    private ProductSpuMapper productSpuMapper;

    @Autowired
    private ProductSkuMapper productSkuMapper;

    @Autowired
    private CategoryMapper categoryMapper;

    @Autowired
    private BrandMapper brandMapper;

    @Autowired
    private ProductAdminSupport productAdminSupport;

    @Autowired
    private ObjectProvider<MarketingReadService> marketingReadServiceProvider;

    @Autowired
    private ObjectProvider<InventoryCommandService> inventoryCommandServiceProvider;

    @Autowired
    private ObjectProvider<InventoryReadService> inventoryReadServiceProvider;

    @Autowired
    private ObjectProvider<ProductSearchSyncService> productSearchSyncServiceProvider;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public AdminProductDetailResponse createProduct(ProductSaveRequest request) {
        productAdminSupport.requireAdminUser();
        validateCategoryAndBrand(request.getCategoryId(), request.getBrandId());

        ProductSpuDO spuDO = new ProductSpuDO();
        spuDO.setCategoryId(request.getCategoryId());
        spuDO.setBrandId(request.getBrandId());
        spuDO.setSpuName(request.getSpuName().trim());
        spuDO.setSubtitle(trimToNull(request.getSubtitle()));
        spuDO.setCoverImage(trimToNull(request.getCoverImage()));
        spuDO.setAlbumImages(joinAlbumImages(request.getAlbumImages()));
        spuDO.setDetail(trimToNull(request.getDetail()));
        spuDO.setPublishStatus(ProductPublishStatusEnum.UNPUBLISHED.getCode());
        spuDO.setSort(request.getSort());
        spuDO.setDeleted(0);

        // insert product spu
        productSpuMapper.insert(spuDO);

        // insert product sku
        List<ProductSkuDO> savedSkuList = saveSkuList(spuDO.getId(), request.getSkuList());

        // insert inventoryStocks
        saveInventoryStocks(savedSkuList, request.getSkuList());
        syncSearchAfterCommit(spuDO.getId());
        return getAdminProductDetail(spuDO.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public AdminProductDetailResponse updateProduct(Long spuId, ProductSaveRequest request) {
        productAdminSupport.requireAdminUser();
        ProductSpuDO spuDO = getSpuOrThrow(spuId);
        validateCategoryAndBrand(request.getCategoryId(), request.getBrandId());

        spuDO.setCategoryId(request.getCategoryId());
        spuDO.setBrandId(request.getBrandId());
        spuDO.setSpuName(request.getSpuName().trim());
        spuDO.setSubtitle(trimToNull(request.getSubtitle()));
        spuDO.setCoverImage(trimToNull(request.getCoverImage()));
        spuDO.setAlbumImages(joinAlbumImages(request.getAlbumImages()));
        spuDO.setDetail(trimToNull(request.getDetail()));
        spuDO.setSort(request.getSort());

        productSpuMapper.updateById(spuDO);
        List<Long> oldSkuIds = listSkuBySpuIds(List.of(spuId), false).getOrDefault(spuId, Collections.emptyList())
                .stream()
                .map(ProductSkuDO::getId)
                .toList();
        deleteInventoryStocks(oldSkuIds);
        markOldSkuDeleted(spuId);
        List<ProductSkuDO> savedSkuList = saveSkuList(spuId, request.getSkuList());
        saveInventoryStocks(savedSkuList, request.getSkuList());
        syncSearchAfterCommit(spuId);
        return getAdminProductDetail(spuId);
    }

    @Override
    public void changePublishStatus(Long spuId, ProductPublishRequest request) {
        productAdminSupport.requireAdminUser();
        if (!Objects.equals(request.getPublishStatus(), ProductPublishStatusEnum.PUBLISHED.getCode())
                && !Objects.equals(request.getPublishStatus(), ProductPublishStatusEnum.UNPUBLISHED.getCode())) {
            throw new BizException(ProductErrorCode.INVALID_PUBLISH_STATUS);
        }

        ProductSpuDO spuDO = getSpuOrThrow(spuId);
        spuDO.setPublishStatus(request.getPublishStatus());
        productSpuMapper.updateById(spuDO);
        syncSearchAfterCommit(spuId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteProduct(Long spuId) {
        productAdminSupport.requireAdminUser();
        ProductSpuDO spuDO = getSpuOrThrow(spuId);
        if (Objects.equals(spuDO.getPublishStatus(), ProductPublishStatusEnum.PUBLISHED.getCode())) {
            throw new BizException(ProductErrorCode.PRODUCT_DELETE_PUBLISHED_FORBIDDEN);
        }

        List<Long> skuIds = productSkuMapper.selectList(Wrappers.<ProductSkuDO>lambdaQuery()
                        .eq(ProductSkuDO::getSpuId, spuId))
                .stream()
                .map(ProductSkuDO::getId)
                .toList();
        deleteInventoryStocks(skuIds);
        productSkuMapper.delete(Wrappers.<ProductSkuDO>lambdaQuery()
                .eq(ProductSkuDO::getSpuId, spuId));
        productSpuMapper.deleteById(spuId);
        deleteSearchAfterCommit(spuId);
    }

    @Override
    public AdminProductDetailResponse getAdminProductDetail(Long spuId) {
        productAdminSupport.requireAdminUser();
        ProductSpuDO spuDO = getSpuOrThrow(spuId);
        List<ProductSkuDO> skuList = listSkuBySpuIds(List.of(spuId), false).getOrDefault(spuId, Collections.emptyList());
        Map<Long, InventoryStockDTO> stockMap = listStockMap(skuList);
        Map<Long, CategoryDO> categoryMap = listCategoryMap(List.of(spuDO.getCategoryId()));
        Map<Long, BrandDO> brandMap = listBrandMap(List.of(spuDO.getBrandId()));
        return buildAdminDetail(spuDO, skuList, stockMap, categoryMap, brandMap);
    }

    @Override
    public PageResponse<AdminProductPageItemResponse> pageAdminProducts(AdminProductPageQueryRequest request) {
        productAdminSupport.requireAdminUser();
        List<Long> categoryIds = resolveCategoryFilterIds(request.getCategoryId(), false);

        Page<ProductSpuDO> page = productSpuMapper.selectPage(
                new Page<>(request.getCurrent(), request.getSize()),
                Wrappers.<ProductSpuDO>lambdaQuery()
                        .in(!categoryIds.isEmpty(), ProductSpuDO::getCategoryId, categoryIds)
                        .eq(request.getBrandId() != null, ProductSpuDO::getBrandId, request.getBrandId())
                        .eq(request.getPublishStatus() != null, ProductSpuDO::getPublishStatus, request.getPublishStatus())
                        .and(hasText(request.getKeyword()), wrapper -> wrapper
                                .like(ProductSpuDO::getSpuName, request.getKeyword().trim())
                                .or()
                                .like(ProductSpuDO::getSubtitle, request.getKeyword().trim()))
                        .orderByAsc(ProductSpuDO::getSort)
                        .orderByDesc(ProductSpuDO::getUpdateTime)
                        .orderByDesc(ProductSpuDO::getId)
        );

        List<ProductSpuDO> records = page.getRecords();
        if (records.isEmpty()) {
            return PageResponse.<AdminProductPageItemResponse>builder()
                    .current(page.getCurrent())
                    .size(page.getSize())
                    .total(page.getTotal())
                    .records(Collections.emptyList())
                    .build();
        }

        List<Long> spuIds = records.stream().map(ProductSpuDO::getId).toList();
        Map<Long, List<ProductSkuDO>> skuMap = listSkuBySpuIds(spuIds, false);
        Map<Long, CategoryDO> categoryMap = listCategoryMap(records.stream().map(ProductSpuDO::getCategoryId).toList());
        Map<Long, BrandDO> brandMap = listBrandMap(records.stream().map(ProductSpuDO::getBrandId).toList());

        List<AdminProductPageItemResponse> responseList = records.stream()
                .map(spu -> buildAdminPageItem(spu, skuMap.getOrDefault(spu.getId(), Collections.emptyList()), categoryMap, brandMap))
                .toList();

        return PageResponse.<AdminProductPageItemResponse>builder()
                .current(page.getCurrent())
                .size(page.getSize())
                .total(page.getTotal())
                .records(responseList)
                .build();
    }

    @Override
    public PageResponse<ProductPageItemResponse> pagePublishedProducts(ProductPageQueryRequest request) {
        List<Long> categoryIds = resolveCategoryFilterIds(request.getCategoryId(), true);
        Page<ProductSpuDO> page = productSpuMapper.selectPage(
                new Page<>(request.getCurrent(), request.getSize()),
                Wrappers.<ProductSpuDO>lambdaQuery()
                        .eq(ProductSpuDO::getPublishStatus, ProductPublishStatusEnum.PUBLISHED.getCode())
                        .in(!categoryIds.isEmpty(), ProductSpuDO::getCategoryId, categoryIds)
                        .eq(request.getBrandId() != null, ProductSpuDO::getBrandId, request.getBrandId())
                        .and(hasText(request.getKeyword()), wrapper -> wrapper
                                .like(ProductSpuDO::getSpuName, request.getKeyword().trim())
                                .or()
                                .like(ProductSpuDO::getSubtitle, request.getKeyword().trim()))
                        .orderByAsc(ProductSpuDO::getSort)
                        .orderByDesc(ProductSpuDO::getUpdateTime)
                        .orderByDesc(ProductSpuDO::getId)
        );

        List<ProductSpuDO> records = page.getRecords();
        if (records.isEmpty()) {
            return PageResponse.<ProductPageItemResponse>builder()
                    .current(page.getCurrent())
                    .size(page.getSize())
                    .total(page.getTotal())
                    .records(Collections.emptyList())
                    .build();
        }

        List<Long> spuIds = records.stream().map(ProductSpuDO::getId).toList();
        Map<Long, List<ProductSkuDO>> skuMap = listSkuBySpuIds(spuIds, true);
        Map<Long, MarketingSkuDiscountDTO> discountMap = listDiscountMap(skuMap);
        Map<Long, CategoryDO> categoryMap = listCategoryMap(records.stream().map(ProductSpuDO::getCategoryId).toList());
        Map<Long, BrandDO> brandMap = listBrandMap(records.stream().map(ProductSpuDO::getBrandId).toList());

        List<ProductPageItemResponse> responseList = records.stream()
                .map(spu -> buildPageItem(spu, skuMap.getOrDefault(spu.getId(), Collections.emptyList()), discountMap, categoryMap, brandMap))
                .toList();

        return PageResponse.<ProductPageItemResponse>builder()
                .current(page.getCurrent())
                .size(page.getSize())
                .total(page.getTotal())
                .records(responseList)
                .build();
    }

    @Override
    public ProductDetailResponse getPublishedProductDetail(Long spuId) {
        ProductSpuDO spuDO = productSpuMapper.selectOne(Wrappers.<ProductSpuDO>lambdaQuery()
                .eq(ProductSpuDO::getId, spuId)
                .eq(ProductSpuDO::getPublishStatus, ProductPublishStatusEnum.PUBLISHED.getCode())
                .last("limit 1"));
        if (spuDO == null) {
            throw new BizException(ProductErrorCode.PRODUCT_NOT_FOUND);
        }

        List<ProductSkuDO> skuList = listSkuBySpuIds(List.of(spuId), true).getOrDefault(spuId, Collections.emptyList());
        Map<Long, MarketingSkuDiscountDTO> discountMap = listDiscountMap(Map.of(spuId, skuList));
        Map<Long, CategoryDO> categoryMap = listCategoryMap(List.of(spuDO.getCategoryId()));
        Map<Long, BrandDO> brandMap = listBrandMap(List.of(spuDO.getBrandId()));
        return buildProductDetail(spuDO, skuList, discountMap, categoryMap, brandMap);
    }

    @Override
    public ProductSkuResponse getPublishedSkuDetail(Long skuId) {
        ProductSkuDO skuDO = productSkuMapper.selectOne(Wrappers.<ProductSkuDO>lambdaQuery()
                .eq(ProductSkuDO::getId, skuId)
                .eq(ProductSkuDO::getStatus, ProductDataStatusEnum.ENABLED.getCode())
                .last("limit 1"));
        if (skuDO == null) {
            throw new BizException(ProductErrorCode.SKU_NOT_FOUND);
        }

        ProductSpuDO spuDO = productSpuMapper.selectOne(Wrappers.<ProductSpuDO>lambdaQuery()
                .eq(ProductSpuDO::getId, skuDO.getSpuId())
                .eq(ProductSpuDO::getPublishStatus, ProductPublishStatusEnum.PUBLISHED.getCode())
                .last("limit 1"));
        if (spuDO == null) {
            throw new BizException(ProductErrorCode.SKU_NOT_FOUND);
        }

        return buildSkuResponse(skuDO, listDiscountMap(Map.of(skuDO.getSpuId(), List.of(skuDO))).get(skuId));
    }

    /**
     * 判断类型和商品id是否为null
     * @param categoryId Long
     * @param brandId Long
     */
    private void validateCategoryAndBrand(Long categoryId, Long brandId) {
        if (categoryMapper.selectById(categoryId) == null) {
            throw new BizException(ProductErrorCode.CATEGORY_NOT_FOUND);
        }
        if (brandMapper.selectById(brandId) == null) {
            throw new BizException(ProductErrorCode.BRAND_NOT_FOUND);
        }
    }

    private ProductSpuDO getSpuOrThrow(Long spuId) {
        ProductSpuDO spuDO = productSpuMapper.selectById(spuId);
        if (spuDO == null) {
            throw new BizException(ProductErrorCode.PRODUCT_NOT_FOUND);
        }
        return spuDO;
    }

    private void markOldSkuDeleted(Long spuId) {
        productSkuMapper.update(null, Wrappers.<ProductSkuDO>lambdaUpdate()
                .eq(ProductSkuDO::getSpuId, spuId)
                .set(ProductSkuDO::getDeleted, 1)
                .set(ProductSkuDO::getIsDefault, 0));
    }

    private List<ProductSkuDO> saveSkuList(Long spuId, List<ProductSkuSaveRequest> skuList) {
        if (skuList == null || skuList.isEmpty()) {
            throw new BizException(ProductErrorCode.SKU_REQUIRED);
        }

        Set<String> codeSet = new HashSet<>();
        List<ProductSkuDO> savedSkuList = new ArrayList<>(skuList.size());
        long defaultCount = skuList.stream().filter(ProductSkuSaveRequest::getDefaultSku).count();
        if (defaultCount > 1) {
            throw new BizException(ProductErrorCode.DEFAULT_SKU_REQUIRED);
        }

        boolean useFirstAsDefault = defaultCount == 0;
        for (int i = 0; i < skuList.size(); i++) {
            ProductSkuSaveRequest skuRequest = skuList.get(i);
            String skuCode = resolveSkuCode(spuId, skuRequest, i);
            if (!codeSet.add(skuCode)) {
                throw new BizException(ProductErrorCode.SKU_CODE_DUPLICATE);
            }

            ProductSkuDO skuDO = new ProductSkuDO();
            skuDO.setSpuId(spuId);
            skuDO.setSkuCode(skuCode);
            skuDO.setSkuName(skuRequest.getSkuName().trim());
            skuDO.setImageUrl(trimToNull(skuRequest.getImageUrl()));
            skuDO.setSalePrice(skuRequest.getSalePrice());
            skuDO.setMarketPrice(skuRequest.getMarketPrice());
            skuDO.setAttrText(trimToNull(skuRequest.getAttrText()));
            skuDO.setIsDefault((useFirstAsDefault && i == 0) || Boolean.TRUE.equals(skuRequest.getDefaultSku()) ? 1 : 0);
            skuDO.setStatus(skuRequest.getStatus());
            skuDO.setDeleted(0);
            productSkuMapper.insert(skuDO);
            savedSkuList.add(skuDO);
        }
        return savedSkuList;
    }

    /**
     * 初始化商品id
     * @param spuId
     * @param skuRequest
     * @param index
     * @return
     */
    private String resolveSkuCode(Long spuId, ProductSkuSaveRequest skuRequest, int index) {
        String requestCode = trimToNull(skuRequest.getSkuCode());
        if (requestCode != null) {
            return requestCode;
        }
        return String.format("SKU-%d-%03d", spuId, index + 1);
    }

    private Map<Long, List<ProductSkuDO>> listSkuBySpuIds(List<Long> spuIds, boolean onlyEnabled) {
        if (spuIds == null || spuIds.isEmpty()) {
            return Collections.emptyMap();
        }
        var wrapper = Wrappers.<ProductSkuDO>lambdaQuery()
                .in(ProductSkuDO::getSpuId, spuIds)
                .orderByDesc(ProductSkuDO::getIsDefault)
                .orderByAsc(ProductSkuDO::getId);
        if (onlyEnabled) {
            wrapper.eq(ProductSkuDO::getStatus, ProductDataStatusEnum.ENABLED.getCode());
        }
        return productSkuMapper.selectList(wrapper).stream()
                .collect(Collectors.groupingBy(ProductSkuDO::getSpuId));
    }

    private Map<Long, CategoryDO> listCategoryMap(List<Long> categoryIds) {
        List<Long> validIds = categoryIds.stream().filter(Objects::nonNull).distinct().toList();
        if (validIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return categoryMapper.selectBatchIds(validIds).stream()
                .collect(Collectors.toMap(CategoryDO::getId, Function.identity()));
    }

    private Map<Long, BrandDO> listBrandMap(List<Long> brandIds) {
        List<Long> validIds = brandIds.stream().filter(Objects::nonNull).distinct().toList();
        if (validIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return brandMapper.selectBatchIds(validIds).stream()
                .collect(Collectors.toMap(BrandDO::getId, Function.identity()));
    }

    private AdminProductPageItemResponse buildAdminPageItem(ProductSpuDO spuDO,
                                                            List<ProductSkuDO> skuList,
                                                            Map<Long, CategoryDO> categoryMap,
                                                            Map<Long, BrandDO> brandMap) {
        PriceRange priceRange = buildPriceRange(skuList);
        CategoryDO categoryDO = categoryMap.get(spuDO.getCategoryId());
        BrandDO brandDO = brandMap.get(spuDO.getBrandId());
        return AdminProductPageItemResponse.builder()
                .spuId(spuDO.getId())
                .spuName(spuDO.getSpuName())
                .subtitle(spuDO.getSubtitle())
                .coverImage(spuDO.getCoverImage())
                .categoryId(spuDO.getCategoryId())
                .categoryName(categoryDO == null ? null : categoryDO.getName())
                .brandId(spuDO.getBrandId())
                .brandName(brandDO == null ? null : brandDO.getName())
                .publishStatus(spuDO.getPublishStatus())
                .sort(spuDO.getSort())
                .skuCount(skuList.size())
                .minSalePrice(priceRange.minPrice())
                .maxSalePrice(priceRange.maxPrice())
                .updateTime(spuDO.getUpdateTime())
                .build();
    }

    private ProductPageItemResponse buildPageItem(ProductSpuDO spuDO,
                                                  List<ProductSkuDO> skuList,
                                                  Map<Long, MarketingSkuDiscountDTO> discountMap,
                                                  Map<Long, CategoryDO> categoryMap,
                                                  Map<Long, BrandDO> brandMap) {
        PriceRange priceRange = buildPriceRange(skuList);
        PriceRange promotionRange = buildPromotionPriceRange(skuList, discountMap);
        CategoryDO categoryDO = categoryMap.get(spuDO.getCategoryId());
        BrandDO brandDO = brandMap.get(spuDO.getBrandId());
        return ProductPageItemResponse.builder()
                .spuId(spuDO.getId())
                .spuName(spuDO.getSpuName())
                .subtitle(spuDO.getSubtitle())
                .coverImage(spuDO.getCoverImage())
                .categoryId(spuDO.getCategoryId())
                .categoryName(categoryDO == null ? null : categoryDO.getName())
                .brandId(spuDO.getBrandId())
                .brandName(brandDO == null ? null : brandDO.getName())
                .minSalePrice(priceRange.minPrice())
                .maxSalePrice(priceRange.maxPrice())
                .minPromotionPrice(promotionRange.minPrice())
                .maxPromotionPrice(promotionRange.maxPrice())
                .build();
    }

    private AdminProductDetailResponse buildAdminDetail(ProductSpuDO spuDO,
                                                        List<ProductSkuDO> skuList,
                                                        Map<Long, InventoryStockDTO> stockMap,
                                                        Map<Long, CategoryDO> categoryMap,
                                                        Map<Long, BrandDO> brandMap) {
        PriceRange priceRange = buildPriceRange(skuList);
        CategoryDO categoryDO = categoryMap.get(spuDO.getCategoryId());
        BrandDO brandDO = brandMap.get(spuDO.getBrandId());
        return AdminProductDetailResponse.builder()
                .spuId(spuDO.getId())
                .spuName(spuDO.getSpuName())
                .subtitle(spuDO.getSubtitle())
                .coverImage(spuDO.getCoverImage())
                .categoryId(spuDO.getCategoryId())
                .categoryName(categoryDO == null ? null : categoryDO.getName())
                .brandId(spuDO.getBrandId())
                .brandName(brandDO == null ? null : brandDO.getName())
                .albumImages(splitAlbumImages(spuDO.getAlbumImages()))
                .detail(spuDO.getDetail())
                .publishStatus(spuDO.getPublishStatus())
                .sort(spuDO.getSort())
                .minSalePrice(priceRange.minPrice())
                .maxSalePrice(priceRange.maxPrice())
                .skuList(skuList.stream()
                        .map(sku -> buildSkuResponse(sku, null, stockMap.get(sku.getId())))
                        .toList())
                .build();
    }

    private ProductDetailResponse buildProductDetail(ProductSpuDO spuDO,
                                                     List<ProductSkuDO> skuList,
                                                     Map<Long, MarketingSkuDiscountDTO> discountMap,
                                                     Map<Long, CategoryDO> categoryMap,
                                                     Map<Long, BrandDO> brandMap) {
        PriceRange priceRange = buildPriceRange(skuList);
        PriceRange promotionRange = buildPromotionPriceRange(skuList, discountMap);
        CategoryDO categoryDO = categoryMap.get(spuDO.getCategoryId());
        BrandDO brandDO = brandMap.get(spuDO.getBrandId());
        return ProductDetailResponse.builder()
                .spuId(spuDO.getId())
                .spuName(spuDO.getSpuName())
                .subtitle(spuDO.getSubtitle())
                .coverImage(spuDO.getCoverImage())
                .categoryId(spuDO.getCategoryId())
                .categoryName(categoryDO == null ? null : categoryDO.getName())
                .brandId(spuDO.getBrandId())
                .brandName(brandDO == null ? null : brandDO.getName())
                .albumImages(splitAlbumImages(spuDO.getAlbumImages()))
                .detail(spuDO.getDetail())
                .minSalePrice(priceRange.minPrice())
                .maxSalePrice(priceRange.maxPrice())
                .minPromotionPrice(promotionRange.minPrice())
                .maxPromotionPrice(promotionRange.maxPrice())
                .skuList(skuList.stream().map(sku -> buildSkuResponse(sku, discountMap.get(sku.getId()), null)).toList())
                .build();
    }

    private ProductSkuResponse buildSkuResponse(ProductSkuDO skuDO,
                                                MarketingSkuDiscountDTO discountDTO,
                                                InventoryStockDTO stockDTO) {
        return ProductSkuResponse.builder()
                .skuId(skuDO.getId())
                .skuCode(skuDO.getSkuCode())
                .skuName(skuDO.getSkuName())
                .imageUrl(skuDO.getImageUrl())
                .salePrice(skuDO.getSalePrice())
                .marketPrice(skuDO.getMarketPrice())
                .promotionPrice(discountDTO == null ? null : discountDTO.getDiscountPrice())
                .promotionActivityId(discountDTO == null ? null : discountDTO.getActivityId())
                .promotionActivityName(discountDTO == null ? null : discountDTO.getActivityName())
                .attrText(skuDO.getAttrText())
                .totalStock(stockDTO == null ? null : stockDTO.getTotalStock())
                .defaultSku(Integer.valueOf(1).equals(skuDO.getIsDefault()))
                .status(skuDO.getStatus())
                .build();
    }

    private ProductSkuResponse buildSkuResponse(ProductSkuDO skuDO, MarketingSkuDiscountDTO discountDTO) {
        return buildSkuResponse(skuDO, discountDTO, null);
    }

    private ProductSkuResponse buildSkuResponse(ProductSkuDO skuDO) {
        return buildSkuResponse(skuDO, null, null);
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
        return marketingReadService.getActiveDiscountMap(skuIds);
    }

    private Map<Long, InventoryStockDTO> listStockMap(List<ProductSkuDO> skuList) {
        InventoryReadService inventoryReadService = inventoryReadServiceProvider.getIfAvailable();
        if (inventoryReadService == null || skuList == null || skuList.isEmpty()) {
            return Collections.emptyMap();
        }
        List<Long> skuIds = skuList.stream()
                .map(ProductSkuDO::getId)
                .distinct()
                .toList();
        return inventoryReadService.getStockMap(skuIds);
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

    private PriceRange buildPromotionPriceRange(List<ProductSkuDO> skuList, Map<Long, MarketingSkuDiscountDTO> discountMap) {
        if (skuList == null || skuList.isEmpty() || discountMap == null || discountMap.isEmpty()) {
            return new PriceRange(null, null);
        }

        List<BigDecimal> prices = skuList.stream()
                .map(sku -> discountMap.get(sku.getId()))
                .filter(Objects::nonNull)
                .map(MarketingSkuDiscountDTO::getDiscountPrice)
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

    private String joinAlbumImages(List<String> albumImages) {
        if (albumImages == null || albumImages.isEmpty()) {
            return null;
        }

        List<String> cleaned = albumImages.stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(item -> !item.isEmpty())
                .toList();
        return cleaned.isEmpty() ? null : String.join(",", cleaned);
    }

    private List<String> splitAlbumImages(String albumImages) {
        if (!hasText(albumImages)) {
            return Collections.emptyList();
        }
        return Arrays.stream(albumImages.split(","))
                .map(String::trim)
                .filter(item -> !item.isEmpty())
                .toList();
    }

    private boolean hasText(String value) {
        return value != null && !value.trim().isEmpty();
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private void syncSearchAfterCommit(Long spuId) {
        if (spuId == null) {
            return;
        }

        // 兜底保护，判断是否有ProductSearchSyncService这个bean
        ProductSearchSyncService syncService = productSearchSyncServiceProvider.getIfAvailable();
        if (syncService == null) {
            return;
        }

        // 如果当前正在一个事务里，不要同步搜索，而是注册一个事务回调，数据库事务执行完之后，再执行
        if (TransactionSynchronizationManager.isActualTransactionActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    syncService.syncBySpuId(spuId);
                }
            });
            return;
        }
        syncService.syncBySpuId(spuId);
    }

    private void deleteSearchAfterCommit(Long spuId) {
        if (spuId == null) {
            return;
        }
        ProductSearchSyncService syncService = productSearchSyncServiceProvider.getIfAvailable();
        if (syncService == null) {
            return;
        }
        if (TransactionSynchronizationManager.isActualTransactionActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    syncService.deleteBySpuId(spuId);
                }
            });
            return;
        }
        syncService.deleteBySpuId(spuId);
    }

    private void deleteInventoryStocks(List<Long> skuIds) {
        if (skuIds == null || skuIds.isEmpty()) {
            return;
        }
        InventoryCommandService inventoryCommandService = inventoryCommandServiceProvider.getIfAvailable();
        if (inventoryCommandService == null) {
            return;
        }
        inventoryCommandService.deleteStocksBySkuIds(skuIds);
    }

    /**
     * 保存库存
     * @param savedSkuList List<ProductSkuDO>
     * @param skuRequests List<ProductSkuSaveRequest>
     */
    private void saveInventoryStocks(List<ProductSkuDO> savedSkuList, List<ProductSkuSaveRequest> skuRequests) {
        if (savedSkuList == null || savedSkuList.isEmpty() || skuRequests == null || skuRequests.isEmpty()) {
            return;
        }
        InventoryCommandService inventoryCommandService = inventoryCommandServiceProvider.getIfAvailable();
        if (inventoryCommandService == null) {
            return;
        }

        List<InventoryStockSaveDTO> stockList = new ArrayList<>(savedSkuList.size());
        for (int i = 0; i < savedSkuList.size(); i++) {
            ProductSkuDO skuDO = savedSkuList.get(i);
            ProductSkuSaveRequest skuRequest = skuRequests.get(i);
            stockList.add(InventoryStockSaveDTO.builder()
                    .skuId(skuDO.getId())
                    .totalStock(skuRequest.getTotalStock())
                    .status(skuRequest.getStatus())
                    .build());
        }
        inventoryCommandService.saveStocks(stockList);
    }

    private List<Long> resolveCategoryFilterIds(Long categoryId, boolean onlyEnabled) {
        if (categoryId == null) {
            return Collections.emptyList();
        }

        var wrapper = Wrappers.<CategoryDO>lambdaQuery()
                .select(CategoryDO::getId, CategoryDO::getParentId);
        if (onlyEnabled) {
            wrapper.eq(CategoryDO::getStatus, ProductDataStatusEnum.ENABLED.getCode());
        }

        List<CategoryDO> categoryList = categoryMapper.selectList(wrapper);
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
