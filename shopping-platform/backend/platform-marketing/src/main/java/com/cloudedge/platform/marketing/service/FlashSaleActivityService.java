package com.cloudedge.platform.marketing.service;

import com.cloudedge.platform.marketing.model.dto.FlashSaleActivityPageQueryRequest;
import com.cloudedge.platform.marketing.model.dto.FlashSaleActivitySaveRequest;
import com.cloudedge.platform.marketing.model.vo.FlashSaleActivityResponse;
import com.cloudedge.platform.marketing.model.vo.PageResponse;
import com.cloudedge.platform.marketing.model.vo.SkuDiscountResponse;

import java.util.List;

public interface FlashSaleActivityService {

    FlashSaleActivityResponse createActivity(FlashSaleActivitySaveRequest request);

    FlashSaleActivityResponse updateActivity(Long activityId, FlashSaleActivitySaveRequest request);

    void deleteActivity(Long activityId);

    PageResponse<FlashSaleActivityResponse> pageActivities(FlashSaleActivityPageQueryRequest request);

    FlashSaleActivityResponse getActivityDetail(Long activityId);

    List<SkuDiscountResponse> listActiveDiscounts(List<Long> skuIds);
}
