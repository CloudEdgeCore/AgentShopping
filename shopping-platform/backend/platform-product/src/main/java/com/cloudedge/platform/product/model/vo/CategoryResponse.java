package com.cloudedge.platform.product.model.vo;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class CategoryResponse {

    private Long id;
    private Long parentId;
    private String name;
    private String iconUrl;
    private Integer sort;
    private Integer status;
    private List<CategoryResponse> children;
}
