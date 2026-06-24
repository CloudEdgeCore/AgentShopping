package com.cloudedge.platform.marketing.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingCouponLockResultDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingOrderItemDTO;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingSkuDiscountDTO;
import com.cloudedge.platform.infrastructure.marketing.service.MarketingOrderService;
import com.cloudedge.platform.marketing.entity.CouponTemplateDO;
import com.cloudedge.platform.marketing.entity.FlashSaleActivityDO;
import com.cloudedge.platform.marketing.entity.FlashSaleOrderRecordDO;
import com.cloudedge.platform.marketing.entity.FlashSaleSkuDO;
import com.cloudedge.platform.marketing.entity.UserCouponDO;
import com.cloudedge.platform.marketing.enums.CouponTypeEnum;
import com.cloudedge.platform.marketing.enums.CouponUserStatusEnum;
import com.cloudedge.platform.marketing.enums.FlashSaleOrderRecordStatusEnum;
import com.cloudedge.platform.marketing.enums.FlashSaleStatusEnum;
import com.cloudedge.platform.marketing.exception.MarketingErrorCode;
import com.cloudedge.platform.marketing.mapper.CouponTemplateMapper;
import com.cloudedge.platform.marketing.mapper.FlashSaleActivityMapper;
import com.cloudedge.platform.marketing.mapper.FlashSaleOrderRecordMapper;
import com.cloudedge.platform.marketing.mapper.FlashSaleSkuMapper;
import com.cloudedge.platform.marketing.mapper.UserCouponMapper;
import com.cloudedge.platform.marketing.support.CouponPricingSupport;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class MarketingOrderServiceImpl implements MarketingOrderService {

    @Autowired
    private FlashSaleActivityMapper flashSaleActivityMapper;

    @Autowired
    private FlashSaleSkuMapper flashSaleSkuMapper;

    @Autowired
    private FlashSaleOrderRecordMapper flashSaleOrderRecordMapper;

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Autowired
    private CouponTemplateMapper couponTemplateMapper;

    @Autowired
    private CouponPricingSupport couponPricingSupport;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<Long, MarketingSkuDiscountDTO> lockOrderSkuDiscounts(String orderNo,
                                                                    Long userId,
                                                                    List<MarketingOrderItemDTO> items) {
        if (items == null || items.isEmpty()) {
            return Collections.emptyMap();
        }

        LocalDateTime now = LocalDateTime.now();
        List<Long> skuIds = items.stream().map(MarketingOrderItemDTO::getSkuId).distinct().toList();
        Map<Long, MarketingOrderItemDTO> itemMap = items.stream()
                .collect(Collectors.toMap(MarketingOrderItemDTO::getSkuId, item -> item));

        List<FlashSaleActivityDO> activityList = flashSaleActivityMapper.selectList(Wrappers.<FlashSaleActivityDO>lambdaQuery()
                .eq(FlashSaleActivityDO::getStatus, FlashSaleStatusEnum.ENABLED.getCode())
                .le(FlashSaleActivityDO::getStartTime, now)
                .ge(FlashSaleActivityDO::getEndTime, now));
        if (activityList.isEmpty()) {
            return Collections.emptyMap();
        }

        Map<Long, FlashSaleActivityDO> activityMap = activityList.stream()
                .collect(Collectors.toMap(FlashSaleActivityDO::getId, item -> item));
        List<Long> activityIds = activityList.stream().map(FlashSaleActivityDO::getId).toList();

        List<FlashSaleSkuDO> candidateSkuList = flashSaleSkuMapper.selectList(Wrappers.<FlashSaleSkuDO>lambdaQuery()
                .in(FlashSaleSkuDO::getActivityId, activityIds)
                .in(FlashSaleSkuDO::getSkuId, skuIds)
                .orderByAsc(FlashSaleSkuDO::getDiscountPrice)
                .orderByAsc(FlashSaleSkuDO::getSort)
                .orderByAsc(FlashSaleSkuDO::getId));

        Map<Long, MarketingSkuDiscountDTO> result = new HashMap<>();
        for (FlashSaleSkuDO skuDO : candidateSkuList) {
            if (result.containsKey(skuDO.getSkuId())) {
                continue;
            }

            MarketingOrderItemDTO item = itemMap.get(skuDO.getSkuId());
            if (item == null || item.getQuantity() == null || item.getQuantity() <= 0) {
                continue;
            }
            if (item.getQuantity() > skuDO.getPerUserLimit()) {
                continue;
            }

            FlashSaleOrderRecordDO existing = flashSaleOrderRecordMapper.selectOne(Wrappers.<FlashSaleOrderRecordDO>lambdaQuery()
                    .eq(FlashSaleOrderRecordDO::getOrderNo, orderNo)
                    .eq(FlashSaleOrderRecordDO::getSkuId, skuDO.getSkuId())
                    .last("limit 1"));
            if (existing != null && FlashSaleOrderRecordStatusEnum.LOCKED.getCode().equals(existing.getStatus())) {
                FlashSaleActivityDO activityDO = activityMap.get(existing.getActivityId());
                result.put(existing.getSkuId(), MarketingSkuDiscountDTO.builder()
                        .skuId(existing.getSkuId())
                        .activityId(existing.getActivityId())
                        .activityName(activityDO == null ? null : activityDO.getName())
                        .discountPrice(existing.getDiscountPrice())
                        .build());
                continue;
            }

            int rows = flashSaleSkuMapper.update(null, Wrappers.<FlashSaleSkuDO>lambdaUpdate()
                    .eq(FlashSaleSkuDO::getId, skuDO.getId())
                    .ge(FlashSaleSkuDO::getActivityStock, item.getQuantity())
                    .setSql("activity_stock = activity_stock - " + item.getQuantity())
                    .setSql("locked_stock = locked_stock + " + item.getQuantity()));
            if (rows <= 0) {
                continue;
            }

            FlashSaleOrderRecordDO recordDO = new FlashSaleOrderRecordDO();
            recordDO.setOrderNo(orderNo);
            recordDO.setActivityId(skuDO.getActivityId());
            recordDO.setSkuId(skuDO.getSkuId());
            recordDO.setQuantity(item.getQuantity());
            recordDO.setDiscountPrice(skuDO.getDiscountPrice());
            recordDO.setStatus(FlashSaleOrderRecordStatusEnum.LOCKED.getCode());
            recordDO.setDeleted(0);
            flashSaleOrderRecordMapper.insert(recordDO);

            FlashSaleActivityDO activityDO = activityMap.get(skuDO.getActivityId());
            result.put(skuDO.getSkuId(), MarketingSkuDiscountDTO.builder()
                    .skuId(skuDO.getSkuId())
                    .activityId(skuDO.getActivityId())
                    .activityName(activityDO == null ? null : activityDO.getName())
                    .discountPrice(skuDO.getDiscountPrice())
                    .build());
        }
        return result;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MarketingCouponLockResultDTO lockUserCoupon(String orderNo,
                                                       Long userId,
                                                       Long userCouponId,
                                                       List<MarketingOrderItemDTO> items) {
        if (userCouponId == null) {
            return null;
        }

        UserCouponDO couponDO = userCouponMapper.selectOne(Wrappers.<UserCouponDO>lambdaQuery()
                .eq(UserCouponDO::getId, userCouponId)
                .eq(UserCouponDO::getUserId, userId)
                .eq(UserCouponDO::getStatus, CouponUserStatusEnum.UNUSED.getCode())
                .last("limit 1"));
        if (couponDO == null) {
            throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_NOT_RECEIVABLE);
        }

        LocalDateTime now = LocalDateTime.now();
        if (now.isBefore(couponDO.getValidFrom()) || now.isAfter(couponDO.getValidTo())) {
            throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_NOT_RECEIVABLE);
        }
        BigDecimal eligibleAmount = couponPricingSupport.calculateEligibleAmount(couponDO, items);
        if (eligibleAmount.compareTo(couponDO.getThresholdAmount()) < 0) {
            throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_NOT_RECEIVABLE);
        }

        BigDecimal couponAmount = couponPricingSupport.calculateCouponAmount(eligibleAmount, couponDO);
        if (couponAmount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new BizException(MarketingErrorCode.INVALID_COUPON_AMOUNT);
        }

        int rows = userCouponMapper.update(null, Wrappers.<UserCouponDO>lambdaUpdate()
                .eq(UserCouponDO::getId, userCouponId)
                .eq(UserCouponDO::getUserId, userId)
                .eq(UserCouponDO::getStatus, CouponUserStatusEnum.UNUSED.getCode())
                .set(UserCouponDO::getStatus, CouponUserStatusEnum.LOCKED.getCode())
                .set(UserCouponDO::getOrderNo, orderNo));
        if (rows <= 0) {
            throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_NOT_RECEIVABLE);
        }

        return MarketingCouponLockResultDTO.builder()
                .userCouponId(couponDO.getId())
                .couponCode(couponDO.getCouponCode())
                .couponName(couponDO.getCouponName())
                .couponAmount(couponAmount)
                .build();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void releaseOrderMarketing(String orderNo) {
        releaseFlashSale(orderNo);
        userCouponMapper.update(null, Wrappers.<UserCouponDO>lambdaUpdate()
                .eq(UserCouponDO::getOrderNo, orderNo)
                .eq(UserCouponDO::getStatus, CouponUserStatusEnum.LOCKED.getCode())
                .set(UserCouponDO::getStatus, CouponUserStatusEnum.UNUSED.getCode())
                .set(UserCouponDO::getOrderNo, null));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void useOrderMarketing(String orderNo) {
        useFlashSale(orderNo);
        userCouponMapper.update(null, Wrappers.<UserCouponDO>lambdaUpdate()
                .eq(UserCouponDO::getOrderNo, orderNo)
                .eq(UserCouponDO::getStatus, CouponUserStatusEnum.LOCKED.getCode())
                .set(UserCouponDO::getStatus, CouponUserStatusEnum.USED.getCode())
                .set(UserCouponDO::getUseTime, LocalDateTime.now()));
    }

    private void releaseFlashSale(String orderNo) {
        List<FlashSaleOrderRecordDO> recordList = flashSaleOrderRecordMapper.selectList(Wrappers.<FlashSaleOrderRecordDO>lambdaQuery()
                .eq(FlashSaleOrderRecordDO::getOrderNo, orderNo)
                .eq(FlashSaleOrderRecordDO::getStatus, FlashSaleOrderRecordStatusEnum.LOCKED.getCode())
                .orderByAsc(FlashSaleOrderRecordDO::getId));
        for (FlashSaleOrderRecordDO record : recordList) {
            int rows = flashSaleSkuMapper.update(null, Wrappers.<FlashSaleSkuDO>lambdaUpdate()
                    .eq(FlashSaleSkuDO::getActivityId, record.getActivityId())
                    .eq(FlashSaleSkuDO::getSkuId, record.getSkuId())
                    .ge(FlashSaleSkuDO::getLockedStock, record.getQuantity())
                    .setSql("activity_stock = activity_stock + " + record.getQuantity())
                    .setSql("locked_stock = locked_stock - " + record.getQuantity()));
            if (rows > 0) {
                flashSaleOrderRecordMapper.update(null, Wrappers.<FlashSaleOrderRecordDO>lambdaUpdate()
                        .eq(FlashSaleOrderRecordDO::getId, record.getId())
                        .eq(FlashSaleOrderRecordDO::getStatus, FlashSaleOrderRecordStatusEnum.LOCKED.getCode())
                        .set(FlashSaleOrderRecordDO::getStatus, FlashSaleOrderRecordStatusEnum.RELEASED.getCode()));
            }
        }
    }

    private void useFlashSale(String orderNo) {
        List<FlashSaleOrderRecordDO> recordList = flashSaleOrderRecordMapper.selectList(Wrappers.<FlashSaleOrderRecordDO>lambdaQuery()
                .eq(FlashSaleOrderRecordDO::getOrderNo, orderNo)
                .eq(FlashSaleOrderRecordDO::getStatus, FlashSaleOrderRecordStatusEnum.LOCKED.getCode())
                .orderByAsc(FlashSaleOrderRecordDO::getId));
        for (FlashSaleOrderRecordDO record : recordList) {
            int rows = flashSaleSkuMapper.update(null, Wrappers.<FlashSaleSkuDO>lambdaUpdate()
                    .eq(FlashSaleSkuDO::getActivityId, record.getActivityId())
                    .eq(FlashSaleSkuDO::getSkuId, record.getSkuId())
                    .ge(FlashSaleSkuDO::getLockedStock, record.getQuantity())
                    .setSql("locked_stock = locked_stock - " + record.getQuantity()));
            if (rows > 0) {
                flashSaleOrderRecordMapper.update(null, Wrappers.<FlashSaleOrderRecordDO>lambdaUpdate()
                        .eq(FlashSaleOrderRecordDO::getId, record.getId())
                        .eq(FlashSaleOrderRecordDO::getStatus, FlashSaleOrderRecordStatusEnum.LOCKED.getCode())
                        .set(FlashSaleOrderRecordDO::getStatus, FlashSaleOrderRecordStatusEnum.USED.getCode()));
            }
        }
    }

}
