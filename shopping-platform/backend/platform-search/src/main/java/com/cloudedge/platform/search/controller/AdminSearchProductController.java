package com.cloudedge.platform.search.controller;

import com.cloudedge.platform.response.Result;
import com.cloudedge.platform.search.service.ProductSearchIndexerService;
import com.cloudedge.platform.search.support.SearchAdminSupport;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/search/product")
@ConditionalOnProperty(prefix = "platform.search", name = "enabled", havingValue = "true")
public class AdminSearchProductController {

    private final ProductSearchIndexerService productSearchIndexerService;
    private final SearchAdminSupport searchAdminSupport;

    public AdminSearchProductController(ProductSearchIndexerService productSearchIndexerService,
                                        SearchAdminSupport searchAdminSupport) {
        this.productSearchIndexerService = productSearchIndexerService;
        this.searchAdminSupport = searchAdminSupport;
    }

    @PostMapping("/rebuild")
    @PreAuthorize("@rbac.hasPermission('search:product:rebuild')")
    public Result<String> rebuildAll() {
        searchAdminSupport.requireAdminUser();
        productSearchIndexerService.rebuildAll();
        return Result.success("product index rebuild done");
    }

    @PostMapping("/sync/{spuId}")
    @PreAuthorize("@rbac.hasPermission('search:product:sync')")
    public Result<String> syncOne(@PathVariable Long spuId) {
        searchAdminSupport.requireAdminUser();
        productSearchIndexerService.syncBySpuId(spuId);
        return Result.success("product index sync done, spuId=" + spuId);
    }
}
