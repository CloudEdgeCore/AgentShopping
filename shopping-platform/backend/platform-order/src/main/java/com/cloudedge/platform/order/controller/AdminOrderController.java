package com.cloudedge.platform.order.controller;

import com.cloudedge.platform.order.model.dto.OrderCancelRequest;
import com.cloudedge.platform.order.model.dto.OrderPageQueryRequest;
import com.cloudedge.platform.order.model.vo.OrderDetailResponse;
import com.cloudedge.platform.order.model.vo.OrderPageItemResponse;
import com.cloudedge.platform.order.model.vo.PageResponse;
import com.cloudedge.platform.order.service.OrderService;
import com.cloudedge.platform.order.support.OrderAdminSupport;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/orders")
public class AdminOrderController {

    private final OrderService orderService;
    private final OrderAdminSupport orderAdminSupport;

    public AdminOrderController(OrderService orderService, OrderAdminSupport orderAdminSupport) {
        this.orderService = orderService;
        this.orderAdminSupport = orderAdminSupport;
    }

    @GetMapping("/page")
    @PreAuthorize("@rbac.hasPermission('oms:order:list')")
    public Result<PageResponse<OrderPageItemResponse>> pageOrders(@Valid OrderPageQueryRequest request) {
        orderAdminSupport.requireAdminUser();
        return Result.success(orderService.pageAdminOrders(request));
    }

    @GetMapping("/{orderNo}")
    @PreAuthorize("@rbac.hasPermission('oms:order:detail')")
    public Result<OrderDetailResponse> getOrderDetail(@PathVariable String orderNo) {
        orderAdminSupport.requireAdminUser();
        return Result.success(orderService.getAdminOrderDetail(orderNo));
    }

    @PostMapping("/{orderNo}/cancel")
    @PreAuthorize("@rbac.hasPermission('oms:order:cancel')")
    public Result<Void> cancelOrder(@PathVariable String orderNo,
                                    @RequestBody(required = false) OrderCancelRequest request) {
        orderAdminSupport.requireAdminUser();
        orderService.adminCancelOrder(orderNo, request);
        return Result.success();
    }
}
