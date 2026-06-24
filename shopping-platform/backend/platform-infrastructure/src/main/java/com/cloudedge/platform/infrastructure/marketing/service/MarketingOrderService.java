package com.cloudedge.platform.infrastructure.marketing.service;

import com.cloudedge.platform.infrastructure.marketing.dto.MarketingCouponLockResultDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingOrderItemDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingSkuDiscountDTO;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public interface MarketingOrderService {

    Map<Long, MarketingSkuDiscountDTO> lockOrderSkuDiscounts(String orderNo, Long userId, List<MarketingOrderItemDTO> items);

    MarketingCouponLockResultDTO lockUserCoupon(String orderNo, Long userId, Long userCouponId, List<MarketingOrderItemDTO> items);

    void releaseOrderMarketing(String orderNo);

    void useOrderMarketing(String orderNo);
}
