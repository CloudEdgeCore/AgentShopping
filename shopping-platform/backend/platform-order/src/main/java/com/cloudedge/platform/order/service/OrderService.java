package com.cloudedge.platform.order.service;

import com.cloudedge.platform.order.model.dto.OrderCancelRequest;
import com.cloudedge.platform.order.model.dto.OrderPageQueryRequest;
import com.cloudedge.platform.order.model.dto.OrderPreviewRequest;
import com.cloudedge.platform.order.model.dto.OrderSubmitRequest;
import com.cloudedge.platform.order.model.vo.OrderDetailResponse;
import com.cloudedge.platform.order.model.vo.OrderPageItemResponse;
import com.cloudedge.platform.order.model.vo.OrderSettlementPreviewResponse;
import com.cloudedge.platform.order.model.vo.OrderSubmitResponse;
import com.cloudedge.platform.order.model.vo.PageResponse;

public interface OrderService {

    OrderSettlementPreviewResponse previewSettlement(OrderPreviewRequest request);

    OrderSubmitResponse submitOrder(OrderSubmitRequest request);

    OrderDetailResponse getOrderDetail(String orderNo);

    PageResponse<OrderPageItemResponse> pageCurrentUserOrders(OrderPageQueryRequest request);

    void cancelOrder(String orderNo, OrderCancelRequest request);

    OrderDetailResponse getAdminOrderDetail(String orderNo);

    PageResponse<OrderPageItemResponse> pageAdminOrders(OrderPageQueryRequest request);

    void adminCancelOrder(String orderNo, OrderCancelRequest request);

    void mockPaySuccess(String orderNo);

    int closeExpiredOrders();
}
