package com.cloudedge.platform.marketing.controller;

import com.cloudedge.platform.marketing.model.dto.CouponTemplatePageQueryRequest;
import com.cloudedge.platform.marketing.model.dto.CouponTemplateSaveRequest;
import com.cloudedge.platform.marketing.enums.CouponTemplateStatusEnum;
import com.cloudedge.platform.marketing.model.vo.CouponTemplateResponse;
import com.cloudedge.platform.marketing.model.vo.PageResponse;
import com.cloudedge.platform.marketing.service.CouponTemplateService;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/marketing/coupon-template")
public class AdminCouponTemplateController {

    @Autowired
    private CouponTemplateService couponTemplateService;

    @PostMapping
    @PreAuthorize("@rbac.hasPermission('sms:coupon:create')")
    public Result<CouponTemplateResponse> createTemplate(@Valid @RequestBody CouponTemplateSaveRequest request) {
        return Result.success(couponTemplateService.createTemplate(request));
    }

    @PutMapping("/{templateId}")
    @PreAuthorize("@rbac.hasPermission('sms:coupon:update')")
    public Result<CouponTemplateResponse> updateTemplate(@PathVariable Long templateId,
                                                         @Valid @RequestBody CouponTemplateSaveRequest request) {
        return Result.success(couponTemplateService.updateTemplate(templateId, request));
    }

    @PutMapping("/{templateId}/enable")
    @PreAuthorize("@rbac.hasPermission('sms:coupon:enable')")
    public Result<Void> enableTemplate(@PathVariable Long templateId) {
        couponTemplateService.changeTemplateStatus(templateId, CouponTemplateStatusEnum.ENABLED.getCode());
        return Result.success();
    }

    @PutMapping("/{templateId}/disable")
    @PreAuthorize("@rbac.hasPermission('sms:coupon:disable')")
    public Result<Void> disableTemplate(@PathVariable Long templateId) {
        couponTemplateService.changeTemplateStatus(templateId, CouponTemplateStatusEnum.DISABLED.getCode());
        return Result.success();
    }

    @GetMapping("/page")
    @PreAuthorize("@rbac.hasPermission('sms:coupon:list')")
    public Result<PageResponse<CouponTemplateResponse>> pageTemplates(@Valid CouponTemplatePageQueryRequest request) {
        return Result.success(couponTemplateService.pageTemplates(request));
    }

    @GetMapping("/{templateId}")
    @PreAuthorize("@rbac.hasPermission('sms:coupon:detail')")
    public Result<CouponTemplateResponse> getTemplateDetail(@PathVariable Long templateId) {
        return Result.success(couponTemplateService.getTemplateDetail(templateId));
    }
}
