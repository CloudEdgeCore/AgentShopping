package com.cloudedge.platform.inventory.controller;

import com.cloudedge.platform.inventory.model.dto.StockCreateRequest;
import com.cloudedge.platform.inventory.model.dto.StockPageQueryRequest;
import com.cloudedge.platform.inventory.model.dto.StockUpdateRequest;
import com.cloudedge.platform.inventory.model.vo.PageResponse;
import com.cloudedge.platform.inventory.model.vo.StockPageItemResponse;
import com.cloudedge.platform.inventory.model.vo.StockResponse;
import com.cloudedge.platform.inventory.service.InventoryAdminService;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/admin/inventory/sku-stock")
public class AdminInventoryController {

    @Autowired
    private InventoryAdminService  inventoryAdminService;

    @PostMapping
    @PreAuthorize("@rbac.hasPermission('wms:stock:create')")
    public Result<StockResponse> createStock(@Valid @RequestBody StockCreateRequest request){
        return Result.success(inventoryAdminService.createStock(request));
    }

    @PutMapping("/{skuId}")
    @PreAuthorize("@rbac.hasPermission('wms:stock:update')")
    public Result<StockResponse> updateStock(@PathVariable Long skuId, @Valid @RequestBody StockUpdateRequest request){
        return Result.success(inventoryAdminService.updateStock(skuId, request));
    }

    @GetMapping("/{skuId}")
    @PreAuthorize("@rbac.hasPermission('wms:stock:list')")
    public Result<StockResponse> getStock(@PathVariable Long skuId){
        return Result.success(inventoryAdminService.getStock(skuId));
    }

    @GetMapping("/page")
    @PreAuthorize("@rbac.hasPermission('wms:stock:list')")
    public Result<PageResponse<StockPageItemResponse>> pageStocks(@Valid StockPageQueryRequest request) {
        return Result.success(inventoryAdminService.pageStocks(request));
    }
}
