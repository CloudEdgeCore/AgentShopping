package com.cloudedge.platform.order.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.infrastructure.cart.dto.CartOrderItemDTO;
import com.cloudedge.platform.infrastructure.cart.service.CartOrderService;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryDeductRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryLockItemDTO;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryLockRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryReleaseRequest;
import com.cloudedge.platform.infrastructure.inventory.dto.InventoryStockDTO;
import com.cloudedge.platform.infrastructure.inventory.service.InventoryCommandService;
import com.cloudedge.platform.infrastructure.inventory.service.InventoryReadService;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingCouponLockResultDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingCouponPreviewDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingOrderItemDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingSkuDiscountDTO;
import com.cloudedge.platform.infrastructure.marketing.service.MarketingOrderService;
import com.cloudedge.platform.infrastructure.marketing.service.MarketingReadService;
import com.cloudedge.platform.infrastructure.payment.service.PaymentOrderService;
import com.cloudedge.platform.infrastructure.product.dto.ProductCartSkuInfo;
import com.cloudedge.platform.infrastructure.product.service.ProductCartReadService;
import com.cloudedge.platform.order.entity.OrderDO;
import com.cloudedge.platform.order.entity.OrderItemDO;
import com.cloudedge.platform.order.enums.OrderStatusEnum;
import com.cloudedge.platform.order.exception.OrderErrorCode;
import com.cloudedge.platform.order.mapper.OrderItemMapper;
import com.cloudedge.platform.order.mapper.OrderMapper;
import com.cloudedge.platform.order.model.dto.OrderCancelRequest;
import com.cloudedge.platform.order.model.dto.OrderPageQueryRequest;
import com.cloudedge.platform.order.model.dto.OrderPreviewRequest;
import com.cloudedge.platform.order.model.dto.OrderSubmitItemRequest;
import com.cloudedge.platform.order.model.dto.OrderSubmitRequest;
import com.cloudedge.platform.order.model.vo.OrderDetailResponse;
import com.cloudedge.platform.order.model.vo.OrderItemResponse;
import com.cloudedge.platform.order.model.vo.OrderPageItemResponse;
import com.cloudedge.platform.order.model.vo.OrderSettlementCouponResponse;
import com.cloudedge.platform.order.model.vo.OrderSettlementItemResponse;
import com.cloudedge.platform.order.model.vo.OrderSettlementPreviewResponse;
import com.cloudedge.platform.order.model.vo.OrderSubmitResponse;
import com.cloudedge.platform.order.model.vo.PageResponse;
import com.cloudedge.platform.order.service.OrderService;
import com.cloudedge.platform.user.entity.UserAddressDO;
import com.cloudedge.platform.user.mapper.UserAddressMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

import static net.logstash.logback.argument.StructuredArguments.kv;

@Service
public class OrderServiceImpl implements OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderServiceImpl.class);
    private static final String ORDER_BIZ_TYPE = "ORDER";
    private static final int ORDER_TIMEOUT_MINUTES = 30;
    private static final String AUTO_CLOSE_REASON = "Payment timeout auto close after 30 minutes";
    private static final String USER_CANCEL_CLOSE_REASON = "Order cancelled by user";
    private static final String ADMIN_CANCEL_CLOSE_REASON = "Order cancelled by admin";
    private static final DateTimeFormatter ORDER_NO_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS");

    private final OrderMapper orderMapper;
    private final OrderItemMapper orderItemMapper;
    private final UserAddressMapper userAddressMapper;
    private final CartOrderService cartOrderService;
    private final ProductCartReadService productCartReadService;
    private final InventoryReadService inventoryReadService;
    private final InventoryCommandService inventoryCommandService;
    private final ObjectProvider<PaymentOrderService> paymentOrderServiceProvider;
    private final ObjectProvider<MarketingOrderService> marketingOrderServiceProvider;
    private final ObjectProvider<MarketingReadService> marketingReadServiceProvider;

    public OrderServiceImpl(OrderMapper orderMapper,
                            OrderItemMapper orderItemMapper,
                            UserAddressMapper userAddressMapper,
                            CartOrderService cartOrderService,
                            ProductCartReadService productCartReadService,
                            InventoryReadService inventoryReadService,
                            InventoryCommandService inventoryCommandService,
                            ObjectProvider<PaymentOrderService> paymentOrderServiceProvider,
                            ObjectProvider<MarketingOrderService> marketingOrderServiceProvider,
                            ObjectProvider<MarketingReadService> marketingReadServiceProvider) {
        this.orderMapper = orderMapper;
        this.orderItemMapper = orderItemMapper;
        this.userAddressMapper = userAddressMapper;
        this.cartOrderService = cartOrderService;
        this.productCartReadService = productCartReadService;
        this.inventoryReadService = inventoryReadService;
        this.inventoryCommandService = inventoryCommandService;
        this.paymentOrderServiceProvider = paymentOrderServiceProvider;
        this.marketingOrderServiceProvider = marketingOrderServiceProvider;
        this.marketingReadServiceProvider = marketingReadServiceProvider;
    }

    @Override
    public OrderSettlementPreviewResponse previewSettlement(OrderPreviewRequest request) {
        Long userId = requireCurrentUserId();
        List<Long> cartItemIds = normalizeCartItemIds(request.getCartItemIds());
        List<OrderSubmitItemRequest> submitItems = resolveSubmitItems(userId, request.getItems(), cartItemIds);
        OrderPricingContext pricing = buildPricingContext(submitItems, listActiveDiscounts(submitItems), true);

        OrderSettlementCouponResponse selectedCoupon = buildSelectedCouponResponse(
                userId,
                request.getUserCouponId(),
                pricing.marketingItems()
        );
        BigDecimal couponAmount = selectedCoupon == null ? BigDecimal.ZERO : safeAmount(selectedCoupon.getCouponAmount());

        return OrderSettlementPreviewResponse.builder()
                .totalQuantity(pricing.totalQuantity())
                .totalAmount(pricing.totalAmount())
                .promotionAmount(pricing.promotionAmount())
                .couponAmount(couponAmount)
                .payableAmount(pricing.amountAfterPromotion().subtract(couponAmount).max(BigDecimal.ZERO))
                .selectedCoupon(selectedCoupon)
                .availableCoupons(listAvailableCoupons(userId, pricing.marketingItems()))
                .items(pricing.items().stream().map(this::buildSettlementItemResponse).toList())
                .build();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public OrderSubmitResponse submitOrder(OrderSubmitRequest request) {
        Long userId = requireCurrentUserId();
        UserAddressDO addressDO = getAddressOrThrow(userId, request.getAddressId());
        List<Long> cartItemIds = normalizeCartItemIds(request.getCartItemIds());
        List<OrderSubmitItemRequest> submitItems = resolveSubmitItems(userId, request.getItems(), cartItemIds);
        String orderNo = generateOrderNo();

        Map<Long, MarketingSkuDiscountDTO> lockedDiscounts = lockOrderDiscounts(orderNo, userId, submitItems);
        OrderPricingContext pricing = buildPricingContext(submitItems, lockedDiscounts, true);
        MarketingCouponLockResultDTO couponResult = lockUserCoupon(orderNo, userId, request.getUserCouponId(), pricing.marketingItems());
        BigDecimal couponAmount = couponResult == null ? BigDecimal.ZERO : safeAmount(couponResult.getCouponAmount());
        BigDecimal payableAmount = pricing.amountAfterPromotion().subtract(couponAmount).max(BigDecimal.ZERO);

        inventoryCommandService.lock(InventoryLockRequest.builder()
                .orderNo(orderNo)
                .bizType(ORDER_BIZ_TYPE)
                .items(pricing.lockItems())
                .build());

        OrderDO orderDO = new OrderDO();
        orderDO.setOrderNo(orderNo);
        orderDO.setUserId(userId);
        orderDO.setAddressId(addressDO.getId());
        orderDO.setStatus(OrderStatusEnum.PENDING_PAYMENT.getCode());
        orderDO.setTotalQuantity(pricing.totalQuantity());
        orderDO.setTotalAmount(pricing.totalAmount());
        orderDO.setPromotionAmount(pricing.promotionAmount());
        orderDO.setCouponAmount(couponAmount);
        orderDO.setPayableAmount(payableAmount);
        orderDO.setCouponUserId(couponResult == null ? null : couponResult.getUserCouponId());
        orderDO.setCouponName(couponResult == null ? null : couponResult.getCouponName());
        orderDO.setReceiverName(addressDO.getReceiverName());
        orderDO.setReceiverMobile(addressDO.getReceiverMobile());
        orderDO.setProvinceName(addressDO.getProvinceName());
        orderDO.setCityName(addressDO.getCityName());
        orderDO.setDistrictName(addressDO.getDistrictName());
        orderDO.setDetailAddress(addressDO.getDetailAddress());
        orderDO.setPostalCode(addressDO.getPostalCode());
        orderDO.setRemark(trimToNull(request.getRemark()));
        orderDO.setDeleted(0);
        orderMapper.insert(orderDO);

        for (OrderPricingItem item : pricing.items()) {
            OrderItemDO itemDO = new OrderItemDO();
            itemDO.setOrderId(orderDO.getId());
            itemDO.setOrderNo(orderNo);
            itemDO.setSkuId(item.skuId());
            itemDO.setSpuId(item.spuId());
            itemDO.setSpuName(item.spuName());
            itemDO.setSkuName(item.skuName());
            itemDO.setSkuImage(item.skuImage());
            itemDO.setSkuAttrText(item.skuAttrText());
            itemDO.setOriginalPrice(item.originalPrice());
            itemDO.setSalePrice(item.salePrice());
            itemDO.setQuantity(item.quantity());
            itemDO.setPromotionAmount(item.promotionAmount());
            itemDO.setTotalAmount(item.totalAmount());
            itemDO.setDeleted(0);
            orderItemMapper.insert(itemDO);
        }

        if (!cartItemIds.isEmpty()) {
            cartOrderService.removeItems(userId, cartItemIds);
        }

        log.info("Order submitted successfully",
                kv("orderNo", orderNo),
                kv("userId", userId),
                kv("totalQuantity", orderDO.getTotalQuantity()),
                kv("payableAmount", orderDO.getPayableAmount()));

        return OrderSubmitResponse.builder()
                .orderNo(orderNo)
                .status(orderDO.getStatus())
                .payableAmount(orderDO.getPayableAmount())
                .build();
    }

    @Override
    public OrderDetailResponse getOrderDetail(String orderNo) {
        Long userId = requireCurrentUserId();
        OrderDO orderDO = getCurrentUserOrderOrThrow(userId, orderNo);
        List<OrderItemDO> itemList = listOrderItems(orderNo);
        return buildDetailResponse(orderDO, itemList);
    }

    @Override
    public PageResponse<OrderPageItemResponse> pageCurrentUserOrders(OrderPageQueryRequest request) {
        Long userId = requireCurrentUserId();
        return pageOrders(request, userId);
    }

    @Override
    public OrderDetailResponse getAdminOrderDetail(String orderNo) {
        OrderDO orderDO = getOrderByNoOrThrow(orderNo);
        List<OrderItemDO> itemList = listOrderItems(orderNo);
        return buildDetailResponse(orderDO, itemList);
    }

    @Override
    public PageResponse<OrderPageItemResponse> pageAdminOrders(OrderPageQueryRequest request) {
        return pageOrders(request, null);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void adminCancelOrder(String orderNo, OrderCancelRequest request) {
        OrderDO orderDO = getOrderByNoOrThrow(orderNo);
        cancelPendingOrder(orderDO, request, ADMIN_CANCEL_CLOSE_REASON);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void cancelOrder(String orderNo, OrderCancelRequest request) {
        Long userId = requireCurrentUserId();
        OrderDO orderDO = getCurrentUserOrderOrThrow(userId, orderNo);
        cancelPendingOrder(orderDO, request, USER_CANCEL_CLOSE_REASON);
    }

    private PageResponse<OrderPageItemResponse> pageOrders(OrderPageQueryRequest request, Long userId) {
        Page<OrderDO> page = orderMapper.selectPage(
                new Page<>(request.getCurrent(), request.getSize()),
                Wrappers.<OrderDO>lambdaQuery()
                        .eq(userId != null, OrderDO::getUserId, userId)
                        .eq(request.getStatus() != null, OrderDO::getStatus, request.getStatus())
                        .orderByDesc(OrderDO::getCreateTime)
                        .orderByDesc(OrderDO::getId)
        );

        if (page.getRecords().isEmpty()) {
            return PageResponse.<OrderPageItemResponse>builder()
                    .current(page.getCurrent())
                    .size(page.getSize())
                    .total(page.getTotal())
                    .records(List.of())
                    .build();
        }

        List<String> orderNos = page.getRecords().stream().map(OrderDO::getOrderNo).toList();
        Map<String, List<OrderItemDO>> itemMap = orderItemMapper.selectList(Wrappers.<OrderItemDO>lambdaQuery()
                        .in(OrderItemDO::getOrderNo, orderNos)
                        .orderByAsc(OrderItemDO::getId))
                .stream()
                .collect(Collectors.groupingBy(OrderItemDO::getOrderNo));

        List<OrderPageItemResponse> records = page.getRecords().stream()
                .map(order -> {
                    List<OrderItemDO> items = itemMap.getOrDefault(order.getOrderNo(), List.of());
                    OrderItemDO firstItem = items.isEmpty() ? null : items.get(0);
                    return OrderPageItemResponse.builder()
                            .orderNo(order.getOrderNo())
                            .status(order.getStatus())
                            .totalQuantity(order.getTotalQuantity())
                            .payableAmount(order.getPayableAmount())
                            .firstSkuName(firstItem == null ? null : firstItem.getSkuName())
                            .firstSkuImage(firstItem == null ? null : firstItem.getSkuImage())
                            .createTime(order.getCreateTime())
                            .build();
                })
                .toList();

        return PageResponse.<OrderPageItemResponse>builder()
                .current(page.getCurrent())
                .size(page.getSize())
                .total(page.getTotal())
                .records(records)
                .build();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void mockPaySuccess(String orderNo) {
        Long userId = requireCurrentUserId();
        OrderDO orderDO = getCurrentUserOrderOrThrow(userId, orderNo);

        if (OrderStatusEnum.PAID.getCode().equals(orderDO.getStatus())) {
            return;
        }
        if (!OrderStatusEnum.PENDING_PAYMENT.getCode().equals(orderDO.getStatus())) {
            throw new BizException(OrderErrorCode.ORDER_STATUS_INVALID);
        }

        int rows = orderMapper.update(null, Wrappers.<OrderDO>lambdaUpdate()
                .eq(OrderDO::getId, orderDO.getId())
                .eq(OrderDO::getStatus, OrderStatusEnum.PENDING_PAYMENT.getCode())
                .set(OrderDO::getStatus, OrderStatusEnum.PAID.getCode())
                .set(OrderDO::getPayTime, LocalDateTime.now()));
        if (rows <= 0) {
            OrderDO latestOrder = orderMapper.selectById(orderDO.getId());
            if (latestOrder != null && OrderStatusEnum.PAID.getCode().equals(latestOrder.getStatus())) {
                return;
            }
            throw new BizException(OrderErrorCode.ORDER_STATUS_INVALID);
        }

        inventoryCommandService.deduct(InventoryDeductRequest.builder()
                .orderNo(orderNo)
                .bizType(ORDER_BIZ_TYPE)
                .build());
        useOrderMarketing(orderNo);

        log.info("Order paid successfully",
                kv("orderNo", orderNo),
                kv("userId", userId),
                kv("payableAmount", orderDO.getPayableAmount()));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int closeExpiredOrders() {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime expireBefore = now.minusMinutes(ORDER_TIMEOUT_MINUTES);

        List<OrderDO> expiredOrders = orderMapper.selectList(Wrappers.<OrderDO>lambdaQuery()
                .eq(OrderDO::getStatus, OrderStatusEnum.PENDING_PAYMENT.getCode())
                .le(OrderDO::getCreateTime, expireBefore)
                .orderByAsc(OrderDO::getId));

        int closedCount = 0;
        for (OrderDO orderDO : expiredOrders) {
            int rows = orderMapper.update(null, Wrappers.<OrderDO>lambdaUpdate()
                    .eq(OrderDO::getId, orderDO.getId())
                    .eq(OrderDO::getStatus, OrderStatusEnum.PENDING_PAYMENT.getCode())
                    .set(OrderDO::getStatus, OrderStatusEnum.CANCELLED.getCode())
                    .set(OrderDO::getCancelReason, AUTO_CLOSE_REASON)
                    .set(OrderDO::getCancelTime, now));
            if (rows <= 0) {
                continue;
            }

            inventoryCommandService.release(InventoryReleaseRequest.builder()
                    .orderNo(orderDO.getOrderNo())
                    .bizType(ORDER_BIZ_TYPE)
                    .build());
            releaseOrderMarketing(orderDO.getOrderNo());
            closeUnpaidPayment(orderDO.getOrderNo(), AUTO_CLOSE_REASON);
            log.info("Expired order closed automatically",
                    kv("orderNo", orderDO.getOrderNo()),
                    kv("reason", AUTO_CLOSE_REASON));
            closedCount++;
        }
        return closedCount;
    }

    private OrderPricingContext buildPricingContext(List<OrderSubmitItemRequest> submitItems,
                                                    Map<Long, MarketingSkuDiscountDTO> discountMap,
                                                    boolean validateStock) {
        List<OrderPricingItem> items = new ArrayList<>();
        List<MarketingOrderItemDTO> marketingItems = new ArrayList<>();
        List<InventoryLockItemDTO> lockItems = new ArrayList<>();
        BigDecimal totalAmount = BigDecimal.ZERO;
        BigDecimal promotionAmount = BigDecimal.ZERO;
        int totalQuantity = 0;

        for (OrderSubmitItemRequest item : submitItems) {
            if (item.getQuantity() == null || item.getQuantity() <= 0) {
                throw new BizException(OrderErrorCode.INVALID_ORDER_QUANTITY);
            }

            ProductCartSkuInfo skuInfo = productCartReadService.getSaleableSkuInfoBySkuId(item.getSkuId());
            if (skuInfo == null) {
                throw new BizException(OrderErrorCode.PRODUCT_NOT_SALEABLE);
            }

            if (validateStock) {
                validateStock(item.getSkuId(), item.getQuantity());
            }

            BigDecimal originalPrice = safeAmount(skuInfo.getSalePrice());
            MarketingSkuDiscountDTO discountDTO = discountMap.get(item.getSkuId());
            BigDecimal salePrice = originalPrice;
            if (discountDTO != null
                    && discountDTO.getDiscountPrice() != null
                    && discountDTO.getDiscountPrice().compareTo(originalPrice) < 0) {
                salePrice = discountDTO.getDiscountPrice();
            }

            BigDecimal originalLineAmount = originalPrice.multiply(BigDecimal.valueOf(item.getQuantity()));
            BigDecimal discountedLineAmount = salePrice.multiply(BigDecimal.valueOf(item.getQuantity()));
            BigDecimal itemPromotionAmount = originalLineAmount.subtract(discountedLineAmount);

            items.add(new OrderPricingItem(
                    skuInfo.getSkuId(),
                    skuInfo.getSpuId(),
                    skuInfo.getCategoryId(),
                    skuInfo.getSpuName(),
                    skuInfo.getSkuName(),
                    skuInfo.getSkuImage(),
                    skuInfo.getSkuAttrText(),
                    item.getQuantity(),
                    originalPrice,
                    salePrice,
                    itemPromotionAmount,
                    discountedLineAmount,
                    discountDTO == null ? null : discountDTO.getActivityId(),
                    discountDTO == null ? null : discountDTO.getActivityName()
            ));

            marketingItems.add(MarketingOrderItemDTO.builder()
                    .skuId(skuInfo.getSkuId())
                    .spuId(skuInfo.getSpuId())
                    .categoryId(skuInfo.getCategoryId())
                    .quantity(item.getQuantity())
                    .amount(discountedLineAmount)
                    .build());

            lockItems.add(InventoryLockItemDTO.builder()
                    .skuId(item.getSkuId())
                    .quantity(item.getQuantity())
                    .build());

            totalAmount = totalAmount.add(originalLineAmount);
            promotionAmount = promotionAmount.add(itemPromotionAmount);
            totalQuantity += item.getQuantity();
        }

        return new OrderPricingContext(
                items,
                marketingItems,
                lockItems,
                totalQuantity,
                totalAmount,
                promotionAmount,
                totalAmount.subtract(promotionAmount).max(BigDecimal.ZERO)
        );
    }

    private void validateStock(Long skuId, Integer quantity) {
        InventoryStockDTO stockDTO = inventoryReadService.getStockBySkuId(skuId);
        if (stockDTO == null
                || stockDTO.getAvailableStock() == null
                || stockDTO.getAvailableStock() < quantity
                || !Integer.valueOf(1).equals(stockDTO.getStatus())) {
            throw new BizException(OrderErrorCode.STOCK_NOT_ENOUGH);
        }
    }

    private Map<Long, MarketingSkuDiscountDTO> listActiveDiscounts(List<OrderSubmitItemRequest> submitItems) {
        MarketingReadService marketingReadService = marketingReadServiceProvider.getIfAvailable();
        if (marketingReadService == null || submitItems == null || submitItems.isEmpty()) {
            return Collections.emptyMap();
        }
        List<Long> skuIds = submitItems.stream().map(OrderSubmitItemRequest::getSkuId).distinct().toList();
        return marketingReadService.getActiveDiscountMap(skuIds);
    }

    private Map<Long, MarketingSkuDiscountDTO> lockOrderDiscounts(String orderNo,
                                                                  Long userId,
                                                                  List<OrderSubmitItemRequest> submitItems) {
        MarketingOrderService marketingOrderService = marketingOrderServiceProvider.getIfAvailable();
        if (marketingOrderService == null) {
            return Collections.emptyMap();
        }
        List<MarketingOrderItemDTO> items = submitItems.stream()
                .map(item -> MarketingOrderItemDTO.builder()
                        .skuId(item.getSkuId())
                        .quantity(item.getQuantity())
                        .build())
                .toList();
        return marketingOrderService.lockOrderSkuDiscounts(orderNo, userId, items);
    }

    private MarketingCouponLockResultDTO lockUserCoupon(String orderNo,
                                                        Long userId,
                                                        Long userCouponId,
                                                        List<MarketingOrderItemDTO> items) {
        if (userCouponId == null) {
            return null;
        }
        MarketingOrderService marketingOrderService = marketingOrderServiceProvider.getIfAvailable();
        if (marketingOrderService == null) {
            return null;
        }
        return marketingOrderService.lockUserCoupon(orderNo, userId, userCouponId, items);
    }

    private OrderSettlementCouponResponse buildSelectedCouponResponse(Long userId,
                                                                      Long userCouponId,
                                                                      List<MarketingOrderItemDTO> items) {
        if (userCouponId == null) {
            return null;
        }
        MarketingReadService marketingReadService = marketingReadServiceProvider.getIfAvailable();
        if (marketingReadService == null) {
            return null;
        }
        return buildCouponResponse(marketingReadService.previewCoupon(userId, userCouponId, items));
    }

    private List<OrderSettlementCouponResponse> listAvailableCoupons(Long userId, List<MarketingOrderItemDTO> items) {
        MarketingReadService marketingReadService = marketingReadServiceProvider.getIfAvailable();
        if (marketingReadService == null) {
            return List.of();
        }
        return marketingReadService.listAvailableCoupons(userId, items).stream()
                .map(this::buildCouponResponse)
                .toList();
    }

    private void releaseOrderMarketing(String orderNo) {
        MarketingOrderService marketingOrderService = marketingOrderServiceProvider.getIfAvailable();
        if (marketingOrderService != null) {
            marketingOrderService.releaseOrderMarketing(orderNo);
        }
    }

    private void useOrderMarketing(String orderNo) {
        MarketingOrderService marketingOrderService = marketingOrderServiceProvider.getIfAvailable();
        if (marketingOrderService != null) {
            marketingOrderService.useOrderMarketing(orderNo);
        }
    }

    private void closeUnpaidPayment(String orderNo, String closeReason) {
        PaymentOrderService paymentOrderService = paymentOrderServiceProvider.getIfAvailable();
        if (paymentOrderService != null) {
            paymentOrderService.closeUnpaidPaymentByOrderNo(orderNo, closeReason);
        }
    }

    private OrderDO getCurrentUserOrderOrThrow(Long userId, String orderNo) {
        OrderDO orderDO = orderMapper.selectOne(Wrappers.<OrderDO>lambdaQuery()
                .eq(OrderDO::getUserId, userId)
                .eq(OrderDO::getOrderNo, orderNo)
                .last("limit 1"));
        if (orderDO == null) {
            throw new BizException(OrderErrorCode.ORDER_NOT_FOUND);
        }
        return orderDO;
    }

    private OrderDO getOrderByNoOrThrow(String orderNo) {
        OrderDO orderDO = orderMapper.selectOne(Wrappers.<OrderDO>lambdaQuery()
                .eq(OrderDO::getOrderNo, orderNo)
                .last("limit 1"));
        if (orderDO == null) {
            throw new BizException(OrderErrorCode.ORDER_NOT_FOUND);
        }
        return orderDO;
    }

    private void cancelPendingOrder(OrderDO orderDO, OrderCancelRequest request, String closeReason) {
        if (!OrderStatusEnum.PENDING_PAYMENT.getCode().equals(orderDO.getStatus())) {
            throw new BizException(OrderErrorCode.ORDER_STATUS_INVALID);
        }

        String cancelReason = trimToNull(request == null ? null : request.getCancelReason());
        if (cancelReason == null) {
            cancelReason = closeReason;
        }

        int rows = orderMapper.update(null, Wrappers.<OrderDO>lambdaUpdate()
                .eq(OrderDO::getId, orderDO.getId())
                .eq(OrderDO::getStatus, OrderStatusEnum.PENDING_PAYMENT.getCode())
                .set(OrderDO::getStatus, OrderStatusEnum.CANCELLED.getCode())
                .set(OrderDO::getCancelReason, cancelReason)
                .set(OrderDO::getCancelTime, LocalDateTime.now()));
        if (rows <= 0) {
            throw new BizException(OrderErrorCode.ORDER_STATUS_INVALID);
        }

        inventoryCommandService.release(InventoryReleaseRequest.builder()
                .orderNo(orderDO.getOrderNo())
                .bizType(ORDER_BIZ_TYPE)
                .build());

        releaseOrderMarketing(orderDO.getOrderNo());
        closeUnpaidPayment(orderDO.getOrderNo(), closeReason);

        log.info("Order cancelled",
                kv("orderNo", orderDO.getOrderNo()),
                kv("reason", cancelReason),
                kv("closeReason", closeReason));
    }

    private UserAddressDO getAddressOrThrow(Long userId, Long addressId) {
        UserAddressDO addressDO = userAddressMapper.selectOne(Wrappers.<UserAddressDO>lambdaQuery()
                .eq(UserAddressDO::getId, addressId)
                .eq(UserAddressDO::getUserId, userId)
                .eq(UserAddressDO::getDeleted, 0)
                .eq(UserAddressDO::getStatus, 1)
                .last("limit 1"));
        if (addressDO == null) {
            throw new BizException(OrderErrorCode.ADDRESS_NOT_FOUND);
        }
        return addressDO;
    }

    private List<OrderSubmitItemRequest> resolveSubmitItems(Long userId,
                                                            List<OrderSubmitItemRequest> requestItems,
                                                            List<Long> cartItemIds) {
        if (!cartItemIds.isEmpty()) {
            List<CartOrderItemDTO> cartItems = cartOrderService.listOrderItems(userId, cartItemIds);
            if (cartItems.size() != cartItemIds.size()) {
                throw new BizException(OrderErrorCode.CART_ITEM_NOT_FOUND);
            }
            return mergeSubmitItems(cartItems.stream().map(item -> {
                OrderSubmitItemRequest requestItem = new OrderSubmitItemRequest();
                requestItem.setSkuId(item.getSkuId());
                requestItem.setQuantity(item.getQuantity());
                return requestItem;
            }).toList());
        }

        if (requestItems == null || requestItems.isEmpty()) {
            throw new BizException(OrderErrorCode.ORDER_ITEM_EMPTY);
        }
        return mergeSubmitItems(requestItems);
    }

    private List<OrderSubmitItemRequest> mergeSubmitItems(List<OrderSubmitItemRequest> items) {
        Map<Long, Integer> quantityMap = new LinkedHashMap<>();
        for (OrderSubmitItemRequest item : items) {
            if (item.getSkuId() == null) {
                continue;
            }
            int quantity = item.getQuantity() == null ? 0 : item.getQuantity();
            quantityMap.merge(item.getSkuId(), quantity, Integer::sum);
        }

        List<OrderSubmitItemRequest> mergedItems = new ArrayList<>(quantityMap.size());
        quantityMap.forEach((skuId, quantity) -> {
            OrderSubmitItemRequest request = new OrderSubmitItemRequest();
            request.setSkuId(skuId);
            request.setQuantity(quantity);
            mergedItems.add(request);
        });
        return mergedItems;
    }

    private List<OrderItemDO> listOrderItems(String orderNo) {
        return orderItemMapper.selectList(Wrappers.<OrderItemDO>lambdaQuery()
                .eq(OrderItemDO::getOrderNo, orderNo)
                .orderByAsc(OrderItemDO::getId));
    }

    private OrderDetailResponse buildDetailResponse(OrderDO orderDO, List<OrderItemDO> itemList) {
        return OrderDetailResponse.builder()
                .orderNo(orderDO.getOrderNo())
                .status(orderDO.getStatus())
                .totalQuantity(orderDO.getTotalQuantity())
                .totalAmount(orderDO.getTotalAmount())
                .promotionAmount(orderDO.getPromotionAmount())
                .couponAmount(orderDO.getCouponAmount())
                .payableAmount(orderDO.getPayableAmount())
                .couponUserId(orderDO.getCouponUserId())
                .couponName(orderDO.getCouponName())
                .receiverName(orderDO.getReceiverName())
                .receiverMobile(orderDO.getReceiverMobile())
                .provinceName(orderDO.getProvinceName())
                .cityName(orderDO.getCityName())
                .districtName(orderDO.getDistrictName())
                .detailAddress(orderDO.getDetailAddress())
                .postalCode(orderDO.getPostalCode())
                .remark(orderDO.getRemark())
                .cancelReason(orderDO.getCancelReason())
                .payTime(orderDO.getPayTime())
                .cancelTime(orderDO.getCancelTime())
                .createTime(orderDO.getCreateTime())
                .items(itemList.stream().map(this::buildItemResponse).toList())
                .build();
    }

    private OrderItemResponse buildItemResponse(OrderItemDO itemDO) {
        return OrderItemResponse.builder()
                .skuId(itemDO.getSkuId())
                .spuId(itemDO.getSpuId())
                .spuName(itemDO.getSpuName())
                .skuName(itemDO.getSkuName())
                .skuImage(itemDO.getSkuImage())
                .skuAttrText(itemDO.getSkuAttrText())
                .originalPrice(itemDO.getOriginalPrice())
                .salePrice(itemDO.getSalePrice())
                .quantity(itemDO.getQuantity())
                .promotionAmount(itemDO.getPromotionAmount())
                .totalAmount(itemDO.getTotalAmount())
                .build();
    }

    private OrderSettlementItemResponse buildSettlementItemResponse(OrderPricingItem item) {
        return OrderSettlementItemResponse.builder()
                .skuId(item.skuId())
                .spuId(item.spuId())
                .spuName(item.spuName())
                .skuName(item.skuName())
                .skuImage(item.skuImage())
                .skuAttrText(item.skuAttrText())
                .quantity(item.quantity())
                .originalPrice(item.originalPrice())
                .salePrice(item.salePrice())
                .promotionAmount(item.promotionAmount())
                .totalAmount(item.totalAmount())
                .promotionActivityId(item.promotionActivityId())
                .promotionActivityName(item.promotionActivityName())
                .build();
    }

    private OrderSettlementCouponResponse buildCouponResponse(MarketingCouponPreviewDTO couponDTO) {
        if (couponDTO == null) {
            return null;
        }
        return OrderSettlementCouponResponse.builder()
                .userCouponId(couponDTO.getUserCouponId())
                .couponCode(couponDTO.getCouponCode())
                .couponName(couponDTO.getCouponName())
                .couponType(couponDTO.getCouponType())
                .thresholdAmount(couponDTO.getThresholdAmount())
                .couponAmount(couponDTO.getCouponAmount())
                .validTo(couponDTO.getValidTo())
                .build();
    }

    private Long requireCurrentUserId() {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BizException(GlobalErrorCode.UNAUTHORIZED);
        }
        return userId;
    }

    private String generateOrderNo() {
        return "ORD"
                + LocalDateTime.now().format(ORDER_NO_FORMATTER)
                + ThreadLocalRandom.current().nextInt(100000, 1000000);
    }

    private List<Long> normalizeCartItemIds(List<Long> cartItemIds) {
        if (cartItemIds == null || cartItemIds.isEmpty()) {
            return Collections.emptyList();
        }
        return cartItemIds.stream().distinct().toList();
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private BigDecimal safeAmount(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }

    private record OrderPricingContext(
            List<OrderPricingItem> items,
            List<MarketingOrderItemDTO> marketingItems,
            List<InventoryLockItemDTO> lockItems,
            Integer totalQuantity,
            BigDecimal totalAmount,
            BigDecimal promotionAmount,
            BigDecimal amountAfterPromotion
    ) {
    }

    private record OrderPricingItem(
            Long skuId,
            Long spuId,
            Long categoryId,
            String spuName,
            String skuName,
            String skuImage,
            String skuAttrText,
            Integer quantity,
            BigDecimal originalPrice,
            BigDecimal salePrice,
            BigDecimal promotionAmount,
            BigDecimal totalAmount,
            Long promotionActivityId,
            String promotionActivityName
    ) {
    }
}
