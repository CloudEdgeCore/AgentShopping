package com.cloudedge.platform.product.controller;

import com.cloudedge.platform.product.model.dto.BrandSaveRequest;
import com.cloudedge.platform.product.model.vo.BrandResponse;
import com.cloudedge.platform.product.service.BrandService;
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

import java.util.List;

@RestController
@RequestMapping("/admin/brand")
public class AdminBrandController {

    @Autowired
    private BrandService brandService;

    @PostMapping
    @PreAuthorize("@rbac.hasPermission('pms:brand:create')")
    public Result<BrandResponse> createBrand(@Valid @RequestBody BrandSaveRequest request) {
        return Result.success(brandService.createBrand(request));
    }

    @PutMapping("/{brandId}")
    @PreAuthorize("@rbac.hasPermission('pms:brand:update')")
    public Result<BrandResponse> updateBrand(@PathVariable Long brandId,
                                             @Valid @RequestBody BrandSaveRequest request) {
        return Result.success(brandService.updateBrand(brandId, request));
    }

    @DeleteMapping("/{brandId}")
    @PreAuthorize("@rbac.hasPermission('pms:brand:delete')")
    public Result<Void> deleteBrand(@PathVariable Long brandId) {
        brandService.deleteBrand(brandId);
        return Result.success();
    }

    @GetMapping("/list")
    @PreAuthorize("@rbac.hasPermission('pms:brand:list')")
    public Result<List<BrandResponse>> listAdminBrands() {
        return Result.success(brandService.listAdminBrands());
    }
}
