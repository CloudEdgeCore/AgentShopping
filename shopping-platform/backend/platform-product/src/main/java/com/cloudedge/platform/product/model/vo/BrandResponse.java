package com.cloudedge.platform.product.model.vo;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class BrandResponse {

    private Long id;
    private String name;
    private String logoUrl;
    private String description;
    private Integer sort;
    private Integer status;
}
