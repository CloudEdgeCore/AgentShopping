package com.cloudedge.platform.order.controller;

import com.cloudedge.platform.order.model.dto.OrderCancelRequest;
import com.cloudedge.platform.order.model.dto.OrderPageQueryRequest;
import com.cloudedge.platform.order.model.dto.OrderPreviewRequest;
import com.cloudedge.platform.order.model.dto.OrderSubmitRequest;
import com.cloudedge.platform.order.model.vo.OrderDetailResponse;
import com.cloudedge.platform.order.model.vo.OrderPageItemResponse;
import com.cloudedge.platform.order.model.vo.PageResponse;
import com.cloudedge.platform.order.model.vo.OrderSettlementPreviewResponse;
import com.cloudedge.platform.order.model.vo.OrderSubmitResponse;
import com.cloudedge.platform.order.service.OrderService;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/orders")
public class OrderController {
    @Autowired
    private OrderService orderService;

    @PostMapping("/preview")
    public Result<OrderSettlementPreviewResponse> previewSettlement(@Valid @RequestBody OrderPreviewRequest request) {
        return Result.success(orderService.previewSettlement(request));
    }

    @PostMapping("/submit")
    public Result<OrderSubmitResponse> submitOrder(@Valid @RequestBody OrderSubmitRequest request) {
        return Result.success(orderService.submitOrder(request));
    }

    @GetMapping("/{orderNo}")
    public Result<OrderDetailResponse> getOrderDetail(@PathVariable String orderNo) {
        return Result.success(orderService.getOrderDetail(orderNo));
    }

    @GetMapping("/page")
    public Result<PageResponse<OrderPageItemResponse>> pageCurrentUserOrders(@Valid OrderPageQueryRequest request) {
        return Result.success(orderService.pageCurrentUserOrders(request));
    }

    @PostMapping("/{orderNo}/cancel")
    public Result<Void> cancelOrder(@PathVariable String orderNo,
                                    @RequestBody(required = false) OrderCancelRequest request) {
        orderService.cancelOrder(orderNo, request);
        return Result.success();
    }
}
