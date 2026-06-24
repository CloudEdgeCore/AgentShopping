package com.cloudedge.platform.marketing.service;

import com.cloudedge.platform.marketing.model.dto.CouponTemplatePageQueryRequest;
import com.cloudedge.platform.marketing.model.dto.CouponTemplateSaveRequest;
import com.cloudedge.platform.marketing.model.vo.CouponTemplateResponse;
import com.cloudedge.platform.marketing.model.vo.PageResponse;

public interface CouponTemplateService {

    CouponTemplateResponse createTemplate(CouponTemplateSaveRequest request);

    CouponTemplateResponse updateTemplate(Long templateId, CouponTemplateSaveRequest request);

    PageResponse<CouponTemplateResponse> pageTemplates(CouponTemplatePageQueryRequest request);

    CouponTemplateResponse getTemplateDetail(Long templateId);

    void changeTemplateStatus(Long templateId, Integer status);
}
