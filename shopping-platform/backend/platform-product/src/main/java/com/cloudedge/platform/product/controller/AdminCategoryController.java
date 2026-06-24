package com.cloudedge.platform.product.controller;

import com.cloudedge.platform.product.model.dto.CategorySaveRequest;
import com.cloudedge.platform.product.model.vo.CategoryResponse;
import com.cloudedge.platform.product.service.CategoryService;
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
@RequestMapping("/admin/category")
public class AdminCategoryController {

    @Autowired
    private CategoryService categoryService;

    @PostMapping
    @PreAuthorize("@rbac.hasPermission('pms:category:create')")
    public Result<CategoryResponse> createCategory(@Valid @RequestBody CategorySaveRequest request) {
        return Result.success(categoryService.createCategory(request));
    }

    @PutMapping("/{categoryId}")
    @PreAuthorize("@rbac.hasPermission('pms:category:update')")
    public Result<CategoryResponse> updateCategory(@PathVariable Long categoryId,
                                                   @Valid @RequestBody CategorySaveRequest request) {
        return Result.success(categoryService.updateCategory(categoryId, request));
    }

    @DeleteMapping("/{categoryId}")
    @PreAuthorize("@rbac.hasPermission('pms:category:delete')")
    public Result<Void> deleteCategory(@PathVariable Long categoryId) {
        categoryService.deleteCategory(categoryId);
        return Result.success(null);
    }

    @GetMapping("/list")
    @PreAuthorize("@rbac.hasPermission('pms:category:list')")
    public Result<List<CategoryResponse>> listAdminCategories() {
        return Result.success(categoryService.listAdminCategories());
    }

    @GetMapping("/tree")
    @PreAuthorize("@rbac.hasPermission('pms:category:list')")
    public Result<List<CategoryResponse>> listAdminCategoryTree() {
        return Result.success(categoryService.listAdminCategoryTree());
    }

}
