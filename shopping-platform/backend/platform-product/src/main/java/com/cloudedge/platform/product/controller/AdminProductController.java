package com.cloudedge.platform.product.controller;

import com.cloudedge.platform.product.model.dto.AdminProductPageQueryRequest;
import com.cloudedge.platform.product.model.dto.ProductPublishRequest;
import com.cloudedge.platform.product.model.dto.ProductSaveRequest;
import com.cloudedge.platform.product.enums.ProductPublishStatusEnum;
import com.cloudedge.platform.product.model.vo.AdminProductDetailResponse;
import com.cloudedge.platform.product.model.vo.AdminProductPageItemResponse;
import com.cloudedge.platform.product.model.vo.PageResponse;
import com.cloudedge.platform.product.service.ProductService;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/product")
public class AdminProductController {

    @Autowired
    private ProductService productService;

    @PostMapping
    @PreAuthorize("@rbac.hasPermission('pms:product:create')")
    public Result<AdminProductDetailResponse> createProduct(@Valid @RequestBody ProductSaveRequest request) {
        return Result.success(productService.createProduct(request));
    }

    @PutMapping("/{spuId}")
    @PreAuthorize("@rbac.hasPermission('pms:product:update')")
    public Result<AdminProductDetailResponse> updateProduct(@PathVariable Long spuId,
                                                            @Valid @RequestBody ProductSaveRequest request) {
        return Result.success(productService.updateProduct(spuId, request));
    }

    @PutMapping("/{spuId}/publish")
    @PreAuthorize("@rbac.hasPermission('pms:product:publish')")
    public Result<Void> changePublishStatus(@PathVariable Long spuId,
                                            @Valid @RequestBody ProductPublishRequest request) {
        productService.changePublishStatus(spuId, request);
        return Result.success();
    }

    @PutMapping("/{spuId}/unpublish")
    @PreAuthorize("@rbac.hasPermission('pms:product:publish')")
    public Result<Void> unpublish(@PathVariable Long spuId) {
        ProductPublishRequest request = new ProductPublishRequest();
        request.setPublishStatus(ProductPublishStatusEnum.UNPUBLISHED.getCode());
        productService.changePublishStatus(spuId, request);
        return Result.success();
    }

    @DeleteMapping("/{spuId}")
    @PreAuthorize("@rbac.hasPermission('pms:product:delete')")
    public Result<Void> deleteProduct(@PathVariable Long spuId) {
        productService.deleteProduct(spuId);
        return Result.success();
    }

    @GetMapping("/{spuId}")
    @PreAuthorize("@rbac.hasPermission('pms:product:detail')")
    public Result<AdminProductDetailResponse> getAdminProductDetail(@PathVariable Long spuId) {
        return Result.success(productService.getAdminProductDetail(spuId));
    }

    @GetMapping("/page")
    @PreAuthorize("@rbac.hasPermission('pms:product:list')")
    public Result<PageResponse<AdminProductPageItemResponse>> pageAdminProducts(@Valid AdminProductPageQueryRequest request) {
        return Result.success(productService.pageAdminProducts(request));
    }
}
