package com.cloudedge.platform.product.controller;

import com.cloudedge.platform.product.model.dto.ProductPageQueryRequest;
import com.cloudedge.platform.product.model.vo.BrandResponse;
import com.cloudedge.platform.product.model.vo.CategoryResponse;
import com.cloudedge.platform.product.model.vo.PageResponse;
import com.cloudedge.platform.product.model.vo.ProductDetailResponse;
import com.cloudedge.platform.product.model.vo.ProductPageItemResponse;
import com.cloudedge.platform.product.model.vo.ProductSkuResponse;
import com.cloudedge.platform.product.service.BrandService;
import com.cloudedge.platform.product.service.CategoryService;
import com.cloudedge.platform.product.service.ProductService;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/product")
public class ProductController {

    @Autowired
    private ProductService productService;

    @Autowired
    private CategoryService categoryService;

    @Autowired
    private BrandService brandService;

    @GetMapping("/categories")
    public Result<List<CategoryResponse>> listEnabledCategories() {
        return Result.success(categoryService.listEnabledCategories());
    }

    @GetMapping("/brands")
    public Result<List<BrandResponse>> listEnabledBrands() {
        return Result.success(brandService.listEnabledBrands());
    }

    @GetMapping("/page")
    public Result<PageResponse<ProductPageItemResponse>> pageProducts(@Valid ProductPageQueryRequest request) {
        return Result.success(productService.pagePublishedProducts(request));
    }

    @GetMapping("/{spuId}")
    public Result<ProductDetailResponse> getProductDetail(@PathVariable Long spuId) {
        return Result.success(productService.getPublishedProductDetail(spuId));
    }

    @GetMapping("/sku/{skuId}")
    public Result<ProductSkuResponse> getSkuDetail(@PathVariable Long skuId) {
        return Result.success(productService.getPublishedSkuDetail(skuId));
    }
}
