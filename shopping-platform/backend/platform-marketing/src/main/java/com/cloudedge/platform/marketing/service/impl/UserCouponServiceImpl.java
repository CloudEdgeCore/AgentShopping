package com.cloudedge.platform.marketing.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.marketing.entity.CouponTemplateDO;
import com.cloudedge.platform.marketing.entity.UserCouponDO;
import com.cloudedge.platform.marketing.enums.CouponTemplateStatusEnum;
import com.cloudedge.platform.marketing.enums.CouponUserStatusEnum;
import com.cloudedge.platform.marketing.exception.MarketingErrorCode;
import com.cloudedge.platform.marketing.mapper.CouponTemplateMapper;
import com.cloudedge.platform.marketing.mapper.UserCouponMapper;
import com.cloudedge.platform.marketing.model.dto.UserCouponPageQueryRequest;
import com.cloudedge.platform.marketing.model.vo.PageResponse;
import com.cloudedge.platform.marketing.model.vo.UserCouponResponse;
import com.cloudedge.platform.marketing.service.UserCouponService;
import com.cloudedge.platform.marketing.support.CouponClaimRedisSupport;
import com.cloudedge.platform.marketing.support.CouponClaimReserveResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class UserCouponServiceImpl implements UserCouponService {

    private static final DateTimeFormatter COUPON_CODE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS");

    @Autowired
    private CouponTemplateMapper couponTemplateMapper;

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Autowired
    private CouponClaimRedisSupport couponClaimRedisSupport;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserCouponResponse claimCoupon(Long templateId) {
        Long userId = requireCurrentUserId();
        CouponTemplateDO templateDO = getReceivableTemplateOrThrow(templateId);

        long userClaimedCount = userCouponMapper.selectCount(Wrappers.<UserCouponDO>lambdaQuery()
                .eq(UserCouponDO::getTemplateId, templateId)
                .eq(UserCouponDO::getUserId, userId));

        CouponClaimReserveResult reserveResult = couponClaimRedisSupport.tryReserve(templateDO, userId, userClaimedCount);
        if (reserveResult == CouponClaimReserveResult.OUT_OF_STOCK) {
            throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_OUT_OF_STOCK);
        }
        if (reserveResult == CouponClaimReserveResult.USER_LIMIT_REACHED) {
            throw new BizException(MarketingErrorCode.COUPON_USER_LIMIT_REACHED);
        }

        boolean reservedInRedis = reserveResult == CouponClaimReserveResult.RESERVED;
        try {
            if (userClaimedCount >= templateDO.getPerUserLimit()) {
                throw new BizException(MarketingErrorCode.COUPON_USER_LIMIT_REACHED);
            }

            int rows = couponTemplateMapper.update(null, Wrappers.<CouponTemplateDO>lambdaUpdate()
                    .eq(CouponTemplateDO::getId, templateId)
                    .eq(CouponTemplateDO::getStatus, CouponTemplateStatusEnum.ENABLED.getCode())
                    .apply("claimed_count < total_count")
                    .setSql("claimed_count = claimed_count + 1"));
            if (rows <= 0) {
                throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_OUT_OF_STOCK);
            }

            UserCouponDO userCouponDO = new UserCouponDO();
            userCouponDO.setTemplateId(templateDO.getId());
            userCouponDO.setUserId(userId);
            userCouponDO.setCouponCode(generateCouponCode());
            userCouponDO.setCouponName(templateDO.getName());
            userCouponDO.setCouponType(templateDO.getCouponType());
            userCouponDO.setThresholdAmount(templateDO.getThresholdAmount());
            userCouponDO.setDiscountAmount(templateDO.getDiscountAmount());
            userCouponDO.setDiscountRate(templateDO.getDiscountRate());
            userCouponDO.setScopeType(templateDO.getScopeType());
            userCouponDO.setStatus(CouponUserStatusEnum.UNUSED.getCode());
            userCouponDO.setReceiveTime(LocalDateTime.now());
            userCouponDO.setValidFrom(templateDO.getValidFrom());
            userCouponDO.setValidTo(templateDO.getValidTo());
            userCouponDO.setDeleted(0);
            userCouponMapper.insert(userCouponDO);
            return buildResponse(userCouponDO);
        } catch (RuntimeException ex) {
            if (reservedInRedis) {
                couponClaimRedisSupport.rollbackReserve(templateId, userId);
            }
            throw ex;
        }
    }

    @Override
    public PageResponse<UserCouponResponse> pageCurrentUserCoupons(UserCouponPageQueryRequest request) {
        Long userId = requireCurrentUserId();
        Page<UserCouponDO> page = userCouponMapper.selectPage(
                new Page<>(request.getCurrent(), request.getSize()),
                Wrappers.<UserCouponDO>lambdaQuery()
                        .eq(UserCouponDO::getUserId, userId)
                        .eq(request.getStatus() != null, UserCouponDO::getStatus, request.getStatus())
                        .orderByDesc(UserCouponDO::getReceiveTime)
                        .orderByDesc(UserCouponDO::getId)
        );

        return PageResponse.<UserCouponResponse>builder()
                .current(page.getCurrent())
                .size(page.getSize())
                .total(page.getTotal())
                .records(page.getRecords().stream().map(this::buildResponse).toList())
                .build();
    }

    private CouponTemplateDO getReceivableTemplateOrThrow(Long templateId) {
        CouponTemplateDO templateDO = couponTemplateMapper.selectById(templateId);
        if (templateDO == null) {
            throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_NOT_FOUND);
        }

        LocalDateTime now = LocalDateTime.now();
        if (!CouponTemplateStatusEnum.ENABLED.getCode().equals(templateDO.getStatus())
                || now.isBefore(templateDO.getReceiveStartTime())
                || now.isAfter(templateDO.getReceiveEndTime())) {
            throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_NOT_RECEIVABLE);
        }
        return templateDO;
    }

    private UserCouponResponse buildResponse(UserCouponDO couponDO) {
        return UserCouponResponse.builder()
                .id(couponDO.getId())
                .templateId(couponDO.getTemplateId())
                .couponCode(couponDO.getCouponCode())
                .couponName(couponDO.getCouponName())
                .couponType(couponDO.getCouponType())
                .thresholdAmount(couponDO.getThresholdAmount())
                .discountAmount(couponDO.getDiscountAmount())
                .discountRate(couponDO.getDiscountRate())
                .scopeType(couponDO.getScopeType())
                .status(couponDO.getStatus())
                .receiveTime(couponDO.getReceiveTime())
                .validFrom(couponDO.getValidFrom())
                .validTo(couponDO.getValidTo())
                .useTime(couponDO.getUseTime())
                .orderNo(couponDO.getOrderNo())
                .build();
    }

    private Long requireCurrentUserId() {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BizException(GlobalErrorCode.UNAUTHORIZED);
        }
        return userId;
    }

    private String generateCouponCode() {
        return "CPN"
                + LocalDateTime.now().format(COUPON_CODE_FORMATTER)
                + ThreadLocalRandom.current().nextInt(1000, 9999);
    }
}
