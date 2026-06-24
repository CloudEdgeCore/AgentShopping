package com.cloudedge.platform.infrastructure.marketing.service;

import com.cloudedge.platform.infrastructure.marketing.dto.MarketingCouponPreviewDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingOrderItemDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingSkuDiscountDTO;

import java.util.List;
import java.util.Map;

public interface MarketingReadService {

    Map<Long, MarketingSkuDiscountDTO> getActiveDiscountMap(List<Long> skuIds);

    MarketingCouponPreviewDTO previewCoupon(Long userId, Long userCouponId, List<MarketingOrderItemDTO> items);

    List<MarketingCouponPreviewDTO> listAvailableCoupons(Long userId, List<MarketingOrderItemDTO> items);
}
