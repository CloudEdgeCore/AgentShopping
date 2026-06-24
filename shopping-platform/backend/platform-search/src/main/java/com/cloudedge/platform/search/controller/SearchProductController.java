package com.cloudedge.platform.search.controller;

import com.cloudedge.platform.product.model.vo.PageResponse;
import com.cloudedge.platform.product.model.vo.ProductPageItemResponse;
import com.cloudedge.platform.response.Result;
import com.cloudedge.platform.search.model.dto.ProductSearchPageQueryRequest;
import com.cloudedge.platform.search.service.ProductSearchQueryService;
import jakarta.validation.Valid;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/search/product")
@ConditionalOnProperty(prefix = "platform.search", name = "enabled", havingValue = "true")
public class SearchProductController {

    private final ProductSearchQueryService productSearchQueryService;

    public SearchProductController(ProductSearchQueryService productSearchQueryService) {
        this.productSearchQueryService = productSearchQueryService;
    }

    @GetMapping("/page")
    public Result<PageResponse<ProductPageItemResponse>> pageProducts(@Valid ProductSearchPageQueryRequest request) {
        return Result.success(productSearchQueryService.pagePublishedProducts(request));
    }
}
