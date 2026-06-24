package com.cloudedge.platform.product.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.product.entity.CategoryDO;
import com.cloudedge.platform.product.entity.ProductSpuDO;
import com.cloudedge.platform.product.enums.ProductDataStatusEnum;
import com.cloudedge.platform.product.exception.ProductErrorCode;
import com.cloudedge.platform.product.mapper.CategoryMapper;
import com.cloudedge.platform.product.mapper.ProductSpuMapper;
import com.cloudedge.platform.product.model.dto.CategorySaveRequest;
import com.cloudedge.platform.product.model.vo.CategoryResponse;
import com.cloudedge.platform.product.service.CategoryService;
import com.cloudedge.platform.product.support.ProductAdminSupport;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class CategoryServiceImpl implements CategoryService {

    @Autowired
    private CategoryMapper categoryMapper;

    @Autowired
    private ProductSpuMapper productSpuMapper;

    @Autowired
    private ProductAdminSupport productAdminSupport;

    @Override
    public CategoryResponse createCategory(CategorySaveRequest request) {
        productAdminSupport.requireAdminUser();
        Long normalizedParentId = normalizeParentId(request.getParentId());
        validateParentCategory(normalizedParentId, null);
        validateDuplicateCategory(normalizedParentId, request.getName(), null);

        CategoryDO categoryDO = new CategoryDO();
        categoryDO.setParentId(normalizedParentId);
        categoryDO.setName(request.getName().trim());
        categoryDO.setIconUrl(trimToNull(request.getIconUrl()));
        categoryDO.setSort(request.getSort());
        categoryDO.setStatus(request.getStatus());
        categoryDO.setDeleted(0);

        categoryMapper.insert(categoryDO);
        return buildResponse(categoryDO);
    }

    @Override
    public CategoryResponse updateCategory(Long categoryId, CategorySaveRequest request) {
        productAdminSupport.requireAdminUser();
        CategoryDO categoryDO = getCategoryOrThrow(categoryId);
        Long normalizedParentId = normalizeParentId(request.getParentId());
        validateParentCategory(normalizedParentId, categoryId);
        validateDuplicateCategory(normalizedParentId, request.getName(), categoryId);

        categoryDO.setParentId(normalizedParentId);
        categoryDO.setName(request.getName().trim());
        categoryDO.setIconUrl(trimToNull(request.getIconUrl()));
        categoryDO.setSort(request.getSort());
        categoryDO.setStatus(request.getStatus());

        categoryMapper.updateById(categoryDO);
        return buildResponse(categoryDO);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteCategory(Long categoryId) {
        productAdminSupport.requireAdminUser();
        getCategoryOrThrow(categoryId);

        List<CategoryDO> allCategories = categoryMapper.selectList(
                Wrappers.<CategoryDO>lambdaQuery()
                        .select(CategoryDO::getId, CategoryDO::getParentId)
        );
        Set<Long> subtreeIds = collectSubtreeIds(categoryId, allCategories);
        validateCategoryNotUsedByProduct(subtreeIds);

        subtreeIds.forEach(categoryMapper::deleteById);
    }

    @Override
    public List<CategoryResponse> listAdminCategories() {
        productAdminSupport.requireAdminUser();
        return listCategories(null);
    }

    @Override
    public List<CategoryResponse> listAdminCategoryTree() {
        productAdminSupport.requireAdminUser();
        return buildCategoryTree(listCategories(null));
    }

    @Override
    public List<CategoryResponse> listEnabledCategories() {
        return buildCategoryTree(listCategories(ProductDataStatusEnum.ENABLED.getCode()));
    }

    private List<CategoryResponse> listCategories(Integer status) {
        var wrapper = Wrappers.<CategoryDO>lambdaQuery()
                .orderByAsc(CategoryDO::getSort)
                .orderByAsc(CategoryDO::getId);
        if (status != null) {
            wrapper.eq(CategoryDO::getStatus, status);
        }
        return categoryMapper.selectList(wrapper).stream()
                .map(this::buildResponse)
                .toList();
    }

    private List<CategoryResponse> buildCategoryTree(List<CategoryResponse> flatCategories) {
        Map<Long, CategoryResponse> nodeMap = new HashMap<>();
        for (CategoryResponse category : flatCategories) {
            nodeMap.put(category.getId(), copyNode(category));
        }

        List<CategoryResponse> roots = new ArrayList<>();
        for (CategoryResponse node : nodeMap.values()) {
            Long normalizedParentId = normalizeParentId(node.getParentId());
            CategoryResponse parent = nodeMap.get(normalizedParentId);
            if (normalizedParentId == 0L || parent == null) {
                roots.add(node);
            } else {
                parent.getChildren().add(node);
            }
        }

        sortTreeNodes(roots);
        return roots;
    }

    private CategoryResponse copyNode(CategoryResponse category) {
        return CategoryResponse.builder()
                .id(category.getId())
                .parentId(category.getParentId())
                .name(category.getName())
                .iconUrl(category.getIconUrl())
                .sort(category.getSort())
                .status(category.getStatus())
                .children(new ArrayList<>())
                .build();
    }

    private void sortTreeNodes(List<CategoryResponse> nodes) {
        nodes.sort(Comparator
                .comparing((CategoryResponse item) -> item.getSort() == null ? 0 : item.getSort())
                .thenComparing(CategoryResponse::getId));
        for (CategoryResponse node : nodes) {
            if (node.getChildren() != null && !node.getChildren().isEmpty()) {
                sortTreeNodes(node.getChildren());
            }
        }
    }

    private CategoryDO getCategoryOrThrow(Long categoryId) {
        CategoryDO categoryDO = categoryMapper.selectById(categoryId);
        if (categoryDO == null) {
            throw new BizException(ProductErrorCode.CATEGORY_NOT_FOUND);
        }
        return categoryDO;
    }

    private void validateDuplicateCategory(Long normalizedParentId, String name, Long excludeId) {
        var wrapper = Wrappers.<CategoryDO>lambdaQuery()
                .eq(CategoryDO::getParentId, normalizedParentId)
                .eq(CategoryDO::getName, name.trim());
        if (excludeId != null) {
            wrapper.ne(CategoryDO::getId, excludeId);
        }
        Long count = categoryMapper.selectCount(wrapper);
        if (count != null && count > 0) {
            throw new BizException(ProductErrorCode.CATEGORY_NAME_EXISTS);
        }
    }

    private void validateParentCategory(Long normalizedParentId, Long currentCategoryId) {
        if (normalizedParentId == 0L) {
            return;
        }

        CategoryDO parentCategory = categoryMapper.selectById(normalizedParentId);
        if (parentCategory == null) {
            throw new BizException(ProductErrorCode.CATEGORY_PARENT_NOT_FOUND);
        }

        if (currentCategoryId == null) {
            return;
        }

        if (currentCategoryId.equals(normalizedParentId)) {
            throw new BizException(ProductErrorCode.CATEGORY_PARENT_INVALID);
        }

        if (isInSubtree(normalizedParentId, currentCategoryId)) {
            throw new BizException(ProductErrorCode.CATEGORY_PARENT_INVALID);
        }
    }

    private boolean isInSubtree(Long candidateParentId, Long currentCategoryId) {
        List<CategoryDO> allCategories = categoryMapper.selectList(
                Wrappers.<CategoryDO>lambdaQuery()
                        .select(CategoryDO::getId, CategoryDO::getParentId)
        );
        Set<Long> subtreeIds = collectSubtreeIds(currentCategoryId, allCategories);
        return subtreeIds.contains(candidateParentId);
    }

    private Set<Long> collectSubtreeIds(Long rootId, List<CategoryDO> allCategories) {
        Map<Long, List<Long>> childrenMap = new HashMap<>();
        for (CategoryDO category : allCategories) {
            Long parentId = normalizeParentId(category.getParentId());
            childrenMap.computeIfAbsent(parentId, key -> new ArrayList<>())
                    .add(category.getId());
        }

        Set<Long> subtreeIds = new LinkedHashSet<>();
        ArrayDeque<Long> queue = new ArrayDeque<>();
        queue.offer(rootId);

        while (!queue.isEmpty()) {
            Long currentId = queue.poll();
            if (!subtreeIds.add(currentId)) {
                continue;
            }
            List<Long> children = childrenMap.get(currentId);
            if (children == null || children.isEmpty()) {
                continue;
            }
            for (Long childId : children) {
                if (childId != null) {
                    queue.offer(childId);
                }
            }
        }
        return subtreeIds;
    }

    private void validateCategoryNotUsedByProduct(Set<Long> categoryIds) {
        if (categoryIds == null || categoryIds.isEmpty()) {
            return;
        }
        Long count = productSpuMapper.selectCount(
                Wrappers.<ProductSpuDO>lambdaQuery()
                        .in(ProductSpuDO::getCategoryId, categoryIds)
        );
        if (count != null && count > 0) {
            throw new BizException(ProductErrorCode.CATEGORY_IN_USE);
        }
    }

    private CategoryResponse buildResponse(CategoryDO categoryDO) {
        return CategoryResponse.builder()
                .id(categoryDO.getId())
                .parentId(categoryDO.getParentId())
                .name(categoryDO.getName())
                .iconUrl(categoryDO.getIconUrl())
                .sort(categoryDO.getSort())
                .status(categoryDO.getStatus())
                .children(new ArrayList<>())
                .build();
    }

    private Long normalizeParentId(Long parentId) {
        return parentId == null ? 0L : parentId;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
