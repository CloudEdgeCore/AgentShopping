package com.cloudedge.platform.product.service;

import com.cloudedge.platform.product.model.dto.AdminProductPageQueryRequest;
import com.cloudedge.platform.product.model.dto.ProductPageQueryRequest;
import com.cloudedge.platform.product.model.dto.ProductPublishRequest;
import com.cloudedge.platform.product.model.dto.ProductSaveRequest;
import com.cloudedge.platform.product.model.vo.AdminProductDetailResponse;
import com.cloudedge.platform.product.model.vo.AdminProductPageItemResponse;
import com.cloudedge.platform.product.model.vo.PageResponse;
import com.cloudedge.platform.product.model.vo.ProductDetailResponse;
import com.cloudedge.platform.product.model.vo.ProductPageItemResponse;
import com.cloudedge.platform.product.model.vo.ProductSkuResponse;

public interface ProductService {

    AdminProductDetailResponse createProduct(ProductSaveRequest request);

    AdminProductDetailResponse updateProduct(Long spuId, ProductSaveRequest request);

    void changePublishStatus(Long spuId, ProductPublishRequest request);

    void deleteProduct(Long spuId);

    AdminProductDetailResponse getAdminProductDetail(Long spuId);

    PageResponse<AdminProductPageItemResponse> pageAdminProducts(AdminProductPageQueryRequest request);

    PageResponse<ProductPageItemResponse> pagePublishedProducts(ProductPageQueryRequest request);

    ProductDetailResponse getPublishedProductDetail(Long spuId);

    ProductSkuResponse getPublishedSkuDetail(Long skuId);
}
