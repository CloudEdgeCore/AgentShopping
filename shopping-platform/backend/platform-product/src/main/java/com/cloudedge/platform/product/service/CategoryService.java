package com.cloudedge.platform.product.service;

import com.cloudedge.platform.product.model.dto.CategorySaveRequest;
import com.cloudedge.platform.product.model.vo.CategoryResponse;

import java.util.List;

public interface CategoryService {

    CategoryResponse createCategory(CategorySaveRequest request);

    CategoryResponse updateCategory(Long categoryId, CategorySaveRequest request);

    void deleteCategory(Long categoryId);

    List<CategoryResponse> listAdminCategories();

    List<CategoryResponse> listAdminCategoryTree();

    List<CategoryResponse> listEnabledCategories();
}
