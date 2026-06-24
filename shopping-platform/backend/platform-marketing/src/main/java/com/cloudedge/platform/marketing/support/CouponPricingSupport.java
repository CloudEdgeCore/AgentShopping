package com.cloudedge.platform.marketing.support;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.infrastructure.marketing.dto.MarketingOrderItemDTO;
import com.cloudedge.platform.marketing.entity.CouponTemplateScopeDO;
import com.cloudedge.platform.marketing.entity.UserCouponDO;
import com.cloudedge.platform.marketing.enums.CouponScopeTypeEnum;
import com.cloudedge.platform.marketing.enums.CouponTypeEnum;
import com.cloudedge.platform.marketing.mapper.CouponTemplateScopeMapper;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Component
public class CouponPricingSupport {

    private final CouponTemplateScopeMapper couponTemplateScopeMapper;

    public CouponPricingSupport(CouponTemplateScopeMapper couponTemplateScopeMapper) {
        this.couponTemplateScopeMapper = couponTemplateScopeMapper;
    }

    public BigDecimal calculateEligibleAmount(UserCouponDO couponDO, List<MarketingOrderItemDTO> items) {
        if (couponDO == null || items == null || items.isEmpty()) {
            return BigDecimal.ZERO;
        }

        if (CouponScopeTypeEnum.ALL.getCode().equals(couponDO.getScopeType())) {
            return sumAmount(items);
        }

        Set<Long> scopeIds = listScopeIds(couponDO.getTemplateId());
        if (scopeIds.isEmpty()) {
            return BigDecimal.ZERO;
        }

        return items.stream()
                .filter(item -> matchScope(couponDO.getScopeType(), scopeIds, item))
                .map(MarketingOrderItemDTO::getAmount)
                .map(this::safeAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    public BigDecimal calculateCouponAmount(BigDecimal eligibleAmount, UserCouponDO couponDO) {
        BigDecimal validAmount = safeAmount(eligibleAmount);
        if (validAmount.compareTo(BigDecimal.ZERO) <= 0 || couponDO == null) {
            return BigDecimal.ZERO;
        }

        if (CouponTypeEnum.FULL_REDUCTION.getCode().equals(couponDO.getCouponType())) {
            return safeAmount(couponDO.getDiscountAmount()).min(validAmount);
        }
        if (CouponTypeEnum.DISCOUNT.getCode().equals(couponDO.getCouponType())) {
            BigDecimal rate = couponDO.getDiscountRate();
            if (rate == null || rate.compareTo(BigDecimal.ZERO) <= 0) {
                return BigDecimal.ZERO;
            }
            BigDecimal payAmount = validAmount.multiply(rate)
                    .divide(new BigDecimal("10"), 2, RoundingMode.HALF_UP);
            return validAmount.subtract(payAmount).max(BigDecimal.ZERO);
        }
        return BigDecimal.ZERO;
    }

    private boolean matchScope(Integer scopeType, Set<Long> scopeIds, MarketingOrderItemDTO item) {
        if (item == null) {
            return false;
        }
        if (CouponScopeTypeEnum.CATEGORY.getCode().equals(scopeType)) {
            return item.getCategoryId() != null && scopeIds.contains(item.getCategoryId());
        }
        if (CouponScopeTypeEnum.SPU.getCode().equals(scopeType)) {
            return item.getSpuId() != null && scopeIds.contains(item.getSpuId());
        }
        if (CouponScopeTypeEnum.SKU.getCode().equals(scopeType)) {
            return item.getSkuId() != null && scopeIds.contains(item.getSkuId());
        }
        return false;
    }

    private Set<Long> listScopeIds(Long templateId) {
        if (templateId == null) {
            return Collections.emptySet();
        }
        return couponTemplateScopeMapper.selectList(Wrappers.<CouponTemplateScopeDO>lambdaQuery()
                        .eq(CouponTemplateScopeDO::getTemplateId, templateId))
                .stream()
                .map(CouponTemplateScopeDO::getScopeId)
                .collect(Collectors.toSet());
    }

    private BigDecimal sumAmount(List<MarketingOrderItemDTO> items) {
        return items.stream()
                .map(MarketingOrderItemDTO::getAmount)
                .map(this::safeAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    private BigDecimal safeAmount(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }
}
