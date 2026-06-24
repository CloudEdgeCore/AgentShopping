package com.cloudedge.platform.marketing.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.marketing.entity.CouponTemplateDO;
import com.cloudedge.platform.marketing.entity.CouponTemplateScopeDO;
import com.cloudedge.platform.marketing.enums.CouponScopeTypeEnum;
import com.cloudedge.platform.marketing.enums.CouponTemplateStatusEnum;
import com.cloudedge.platform.marketing.enums.CouponTypeEnum;
import com.cloudedge.platform.marketing.exception.MarketingErrorCode;
import com.cloudedge.platform.marketing.mapper.CouponTemplateMapper;
import com.cloudedge.platform.marketing.mapper.CouponTemplateScopeMapper;
import com.cloudedge.platform.marketing.model.dto.CouponTemplatePageQueryRequest;
import com.cloudedge.platform.marketing.model.dto.CouponTemplateSaveRequest;
import com.cloudedge.platform.marketing.model.vo.CouponTemplateResponse;
import com.cloudedge.platform.marketing.model.vo.PageResponse;
import com.cloudedge.platform.marketing.service.CouponTemplateService;
import com.cloudedge.platform.marketing.support.MarketingAdminSupport;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.List;

@Service
public class CouponTemplateServiceImpl implements CouponTemplateService {

    @Autowired
    private CouponTemplateMapper couponTemplateMapper;

    @Autowired
    private CouponTemplateScopeMapper couponTemplateScopeMapper;

    @Autowired
    private MarketingAdminSupport marketingAdminSupport;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CouponTemplateResponse createTemplate(CouponTemplateSaveRequest request) {
        marketingAdminSupport.requireAdminUser();
        validateTemplateRequest(request);

        CouponTemplateDO templateDO = new CouponTemplateDO();
        templateDO.setName(request.getName().trim());
        templateDO.setCouponType(request.getCouponType());
        templateDO.setThresholdAmount(safeAmount(request.getThresholdAmount()));
        templateDO.setDiscountAmount(safeAmount(request.getDiscountAmount()));
        templateDO.setDiscountRate(request.getDiscountRate());
        templateDO.setTotalCount(request.getTotalCount());
        templateDO.setClaimedCount(0);
        templateDO.setPerUserLimit(request.getPerUserLimit());
        templateDO.setScopeType(request.getScopeType());
        templateDO.setReceiveStartTime(request.getReceiveStartTime());
        templateDO.setReceiveEndTime(request.getReceiveEndTime());
        templateDO.setValidFrom(request.getValidFrom());
        templateDO.setValidTo(request.getValidTo());
        templateDO.setDescription(trimToNull(request.getDescription()));
        templateDO.setStatus(request.getStatus());
        templateDO.setDeleted(0);
        couponTemplateMapper.insert(templateDO);

        saveScopes(templateDO.getId(), request.getScopeType(), request.getScopeIds());
        return buildResponse(templateDO, normalizeScopeIds(request.getScopeType(), request.getScopeIds()));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CouponTemplateResponse updateTemplate(Long templateId, CouponTemplateSaveRequest request) {
        marketingAdminSupport.requireAdminUser();
        validateTemplateRequest(request);

        CouponTemplateDO templateDO = getTemplateOrThrow(templateId);
        if (request.getTotalCount() < templateDO.getClaimedCount()) {
            throw new BizException(MarketingErrorCode.INVALID_COUPON_AMOUNT);
        }

        templateDO.setName(request.getName().trim());
        templateDO.setCouponType(request.getCouponType());
        templateDO.setThresholdAmount(safeAmount(request.getThresholdAmount()));
        templateDO.setDiscountAmount(safeAmount(request.getDiscountAmount()));
        templateDO.setDiscountRate(request.getDiscountRate());
        templateDO.setTotalCount(request.getTotalCount());
        templateDO.setPerUserLimit(request.getPerUserLimit());
        templateDO.setScopeType(request.getScopeType());
        templateDO.setReceiveStartTime(request.getReceiveStartTime());
        templateDO.setReceiveEndTime(request.getReceiveEndTime());
        templateDO.setValidFrom(request.getValidFrom());
        templateDO.setValidTo(request.getValidTo());
        templateDO.setDescription(trimToNull(request.getDescription()));
        templateDO.setStatus(request.getStatus());
        couponTemplateMapper.updateById(templateDO);

        couponTemplateScopeMapper.delete(Wrappers.<CouponTemplateScopeDO>lambdaQuery()
                .eq(CouponTemplateScopeDO::getTemplateId, templateId));
        saveScopes(templateDO.getId(), request.getScopeType(), request.getScopeIds());
        return buildResponse(templateDO, normalizeScopeIds(request.getScopeType(), request.getScopeIds()));
    }

    @Override
    public PageResponse<CouponTemplateResponse> pageTemplates(CouponTemplatePageQueryRequest request) {
        marketingAdminSupport.requireAdminUser();

        Page<CouponTemplateDO> page = couponTemplateMapper.selectPage(
                new Page<>(request.getCurrent(), request.getSize()),
                Wrappers.<CouponTemplateDO>lambdaQuery()
                        .eq(request.getStatus() != null, CouponTemplateDO::getStatus, request.getStatus())
                        .orderByDesc(CouponTemplateDO::getCreateTime)
                        .orderByDesc(CouponTemplateDO::getId)
        );

        List<CouponTemplateResponse> records = page.getRecords().stream()
                .map(template -> buildResponse(template, Collections.emptyList()))
                .toList();

        return PageResponse.<CouponTemplateResponse>builder()
                .current(page.getCurrent())
                .size(page.getSize())
                .total(page.getTotal())
                .records(records)
                .build();
    }

    @Override
    public CouponTemplateResponse getTemplateDetail(Long templateId) {
        marketingAdminSupport.requireAdminUser();
        CouponTemplateDO templateDO = getTemplateOrThrow(templateId);
        List<Long> scopeIds = couponTemplateScopeMapper.selectList(Wrappers.<CouponTemplateScopeDO>lambdaQuery()
                        .eq(CouponTemplateScopeDO::getTemplateId, templateId)
                        .orderByAsc(CouponTemplateScopeDO::getId))
                .stream()
                .map(CouponTemplateScopeDO::getScopeId)
                .toList();
        return buildResponse(templateDO, scopeIds);
    }

    @Override
    public void changeTemplateStatus(Long templateId, Integer status) {
        marketingAdminSupport.requireAdminUser();
        if (!CouponTemplateStatusEnum.ENABLED.getCode().equals(status)
                && !CouponTemplateStatusEnum.DISABLED.getCode().equals(status)) {
            throw new BizException(MarketingErrorCode.INVALID_COUPON_AMOUNT);
        }
        CouponTemplateDO templateDO = getTemplateOrThrow(templateId);
        templateDO.setStatus(status);
        couponTemplateMapper.updateById(templateDO);
    }

    private CouponTemplateDO getTemplateOrThrow(Long templateId) {
        CouponTemplateDO templateDO = couponTemplateMapper.selectById(templateId);
        if (templateDO == null) {
            throw new BizException(MarketingErrorCode.COUPON_TEMPLATE_NOT_FOUND);
        }
        return templateDO;
    }

    private void validateTemplateRequest(CouponTemplateSaveRequest request) {
        if (request.getReceiveEndTime().isBefore(request.getReceiveStartTime())
                || request.getValidTo().isBefore(request.getValidFrom())) {
            throw new BizException(MarketingErrorCode.INVALID_ACTIVITY_TIME);
        }

        if (CouponTypeEnum.FULL_REDUCTION.getCode().equals(request.getCouponType())) {
            if (request.getDiscountAmount() == null || request.getDiscountAmount().compareTo(BigDecimal.ZERO) <= 0) {
                throw new BizException(MarketingErrorCode.INVALID_COUPON_AMOUNT);
            }
        } else if (CouponTypeEnum.DISCOUNT.getCode().equals(request.getCouponType())) {
            if (request.getDiscountRate() == null
                    || request.getDiscountRate().compareTo(BigDecimal.ZERO) <= 0
                    || request.getDiscountRate().compareTo(new BigDecimal("10")) > 0) {
                throw new BizException(MarketingErrorCode.INVALID_COUPON_AMOUNT);
            }
        } else {
            throw new BizException(MarketingErrorCode.INVALID_COUPON_AMOUNT);
        }

        if (!CouponScopeTypeEnum.ALL.getCode().equals(request.getScopeType())
                && (request.getScopeIds() == null || request.getScopeIds().isEmpty())) {
            throw new BizException(MarketingErrorCode.INVALID_COUPON_SCOPE);
        }
    }

    private void saveScopes(Long templateId, Integer scopeType, List<Long> scopeIds) {
        if (CouponScopeTypeEnum.ALL.getCode().equals(scopeType)) {
            return;
        }
        for (Long scopeId : normalizeScopeIds(scopeType, scopeIds)) {
            CouponTemplateScopeDO scopeDO = new CouponTemplateScopeDO();
            scopeDO.setTemplateId(templateId);
            scopeDO.setScopeType(scopeType);
            scopeDO.setScopeId(scopeId);
            scopeDO.setDeleted(0);
            couponTemplateScopeMapper.insert(scopeDO);
        }
    }

    private List<Long> normalizeScopeIds(Integer scopeType, List<Long> scopeIds) {
        if (CouponScopeTypeEnum.ALL.getCode().equals(scopeType) || scopeIds == null || scopeIds.isEmpty()) {
            return Collections.emptyList();
        }
        return scopeIds.stream().distinct().toList();
    }

    private CouponTemplateResponse buildResponse(CouponTemplateDO templateDO, List<Long> scopeIds) {
        return CouponTemplateResponse.builder()
                .id(templateDO.getId())
                .name(templateDO.getName())
                .couponType(templateDO.getCouponType())
                .thresholdAmount(templateDO.getThresholdAmount())
                .discountAmount(templateDO.getDiscountAmount())
                .discountRate(templateDO.getDiscountRate())
                .totalCount(templateDO.getTotalCount())
                .claimedCount(templateDO.getClaimedCount())
                .perUserLimit(templateDO.getPerUserLimit())
                .scopeType(templateDO.getScopeType())
                .scopeIds(scopeIds)
                .receiveStartTime(templateDO.getReceiveStartTime())
                .receiveEndTime(templateDO.getReceiveEndTime())
                .validFrom(templateDO.getValidFrom())
                .validTo(templateDO.getValidTo())
                .description(templateDO.getDescription())
                .status(templateDO.getStatus())
                .build();
    }

    private BigDecimal safeAmount(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
