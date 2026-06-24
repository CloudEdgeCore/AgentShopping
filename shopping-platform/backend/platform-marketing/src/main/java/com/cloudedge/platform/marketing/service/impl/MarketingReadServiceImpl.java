package com.cloudedge.platform.marketing.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingCouponPreviewDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingOrderItemDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingSkuDiscountDTO;
import com.cloudedge.platform.infrastructure.marketing.service.MarketingReadService;
import com.cloudedge.platform.marketing.entity.UserCouponDO;
import com.cloudedge.platform.marketing.enums.CouponUserStatusEnum;
import com.cloudedge.platform.marketing.mapper.UserCouponMapper;
import com.cloudedge.platform.marketing.model.vo.SkuDiscountResponse;
import com.cloudedge.platform.marketing.service.FlashSaleActivityService;
import com.cloudedge.platform.marketing.support.CouponPricingSupport;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Comparator;
import java.util.stream.Collectors;

@Service
public class MarketingReadServiceImpl implements MarketingReadService {

    private final FlashSaleActivityService flashSaleActivityService;
    private final UserCouponMapper userCouponMapper;
    private final CouponPricingSupport couponPricingSupport;

    public MarketingReadServiceImpl(FlashSaleActivityService flashSaleActivityService,
                                    UserCouponMapper userCouponMapper,
                                    CouponPricingSupport couponPricingSupport) {
        this.flashSaleActivityService = flashSaleActivityService;
        this.userCouponMapper = userCouponMapper;
        this.couponPricingSupport = couponPricingSupport;
    }

    @Override
    public Map<Long, MarketingSkuDiscountDTO> getActiveDiscountMap(List<Long> skuIds) {
        if (skuIds == null || skuIds.isEmpty()) {
            return Collections.emptyMap();
        }
        List<SkuDiscountResponse> discounts = flashSaleActivityService.listActiveDiscounts(skuIds);
        return discounts.stream().collect(Collectors.toMap(
                SkuDiscountResponse::getSkuId,
                item -> MarketingSkuDiscountDTO.builder()
                        .skuId(item.getSkuId())
                        .activityId(item.getActivityId())
                        .activityName(item.getActivityName())
                        .discountPrice(item.getDiscountPrice())
                        .build(),
                (a, b) -> a
        ));
    }

    @Override
    public MarketingCouponPreviewDTO previewCoupon(Long userId, Long userCouponId, List<MarketingOrderItemDTO> items) {
        if (userId == null || userCouponId == null) {
            return null;
        }
        UserCouponDO couponDO = getPreviewableCoupon(userId, userCouponId);
        if (couponDO == null) {
            return null;
        }
        BigDecimal eligibleAmount = couponPricingSupport.calculateEligibleAmount(couponDO, items);
        if (eligibleAmount.compareTo(couponDO.getThresholdAmount()) < 0) {
            return null;
        }
        BigDecimal couponAmount = couponPricingSupport.calculateCouponAmount(eligibleAmount, couponDO);
        if (couponAmount.compareTo(BigDecimal.ZERO) <= 0) {
            return null;
        }
        return buildCouponPreview(couponDO, couponAmount);
    }

    @Override
    public List<MarketingCouponPreviewDTO> listAvailableCoupons(Long userId, List<MarketingOrderItemDTO> items) {
        if (userId == null) {
            return Collections.emptyList();
        }

        LocalDateTime now = LocalDateTime.now();
        return userCouponMapper.selectList(Wrappers.<UserCouponDO>lambdaQuery()
                        .eq(UserCouponDO::getUserId, userId)
                        .eq(UserCouponDO::getStatus, CouponUserStatusEnum.UNUSED.getCode())
                        .le(UserCouponDO::getValidFrom, now)
                        .ge(UserCouponDO::getValidTo, now)
                        .orderByAsc(UserCouponDO::getValidTo)
                        .orderByDesc(UserCouponDO::getId))
                .stream()
                .map(couponDO -> {
                    BigDecimal eligibleAmount = couponPricingSupport.calculateEligibleAmount(couponDO, items);
                    if (eligibleAmount.compareTo(couponDO.getThresholdAmount()) < 0) {
                        return null;
                    }
                    BigDecimal couponAmount = couponPricingSupport.calculateCouponAmount(eligibleAmount, couponDO);
                    if (couponAmount.compareTo(BigDecimal.ZERO) <= 0) {
                        return null;
                    }
                    return buildCouponPreview(couponDO, couponAmount);
                })
                .filter(java.util.Objects::nonNull)
                .sorted(Comparator.comparing(MarketingCouponPreviewDTO::getCouponAmount, Comparator.reverseOrder())
                        .thenComparing(MarketingCouponPreviewDTO::getValidTo))
                .toList();
    }

    private UserCouponDO getPreviewableCoupon(Long userId, Long userCouponId) {
        LocalDateTime now = LocalDateTime.now();
        return userCouponMapper.selectOne(Wrappers.<UserCouponDO>lambdaQuery()
                .eq(UserCouponDO::getId, userCouponId)
                .eq(UserCouponDO::getUserId, userId)
                .eq(UserCouponDO::getStatus, CouponUserStatusEnum.UNUSED.getCode())
                .le(UserCouponDO::getValidFrom, now)
                .ge(UserCouponDO::getValidTo, now)
                .last("limit 1"));
    }

    private MarketingCouponPreviewDTO buildCouponPreview(UserCouponDO couponDO, BigDecimal couponAmount) {
        return MarketingCouponPreviewDTO.builder()
                .userCouponId(couponDO.getId())
                .couponCode(couponDO.getCouponCode())
                .couponName(couponDO.getCouponName())
                .couponType(couponDO.getCouponType())
                .thresholdAmount(couponDO.getThresholdAmount())
                .couponAmount(couponAmount)
                .validTo(couponDO.getValidTo())
                .build();
    }
}
