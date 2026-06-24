package com.cloudedge.platform.marketing.controller;

import com.cloudedge.platform.marketing.model.dto.FlashSaleActivityPageQueryRequest;
import com.cloudedge.platform.marketing.model.dto.FlashSaleActivitySaveRequest;
import com.cloudedge.platform.marketing.model.vo.FlashSaleActivityResponse;
import com.cloudedge.platform.marketing.model.vo.PageResponse;
import com.cloudedge.platform.marketing.service.FlashSaleActivityService;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/marketing/flash-sale")
public class AdminFlashSaleActivityController {

    @Autowired
    private FlashSaleActivityService flashSaleActivityService;

    @PostMapping
    @PreAuthorize("@rbac.hasPermission('sms:flashsale:create')")
    public Result<FlashSaleActivityResponse> createActivity(@Valid @RequestBody FlashSaleActivitySaveRequest request) {
        return Result.success(flashSaleActivityService.createActivity(request));
    }

    @PutMapping("/{activityId}")
    @PreAuthorize("@rbac.hasPermission('sms:flashsale:update')")
    public Result<FlashSaleActivityResponse> updateActivity(@PathVariable Long activityId,
                                                            @Valid @RequestBody FlashSaleActivitySaveRequest request) {
        return Result.success(flashSaleActivityService.updateActivity(activityId, request));
    }

    @DeleteMapping("/{activityId}")
    @PreAuthorize("@rbac.hasPermission('sms:flashsale:delete')")
    public Result<Void> deleteActivity(@PathVariable Long activityId) {
        flashSaleActivityService.deleteActivity(activityId);
        return Result.success();
    }

    @GetMapping("/page")
    @PreAuthorize("@rbac.hasPermission('sms:flashsale:list')")
    public Result<PageResponse<FlashSaleActivityResponse>> pageActivities(@Valid FlashSaleActivityPageQueryRequest request) {
        return Result.success(flashSaleActivityService.pageActivities(request));
    }

    @GetMapping("/{activityId}")
    @PreAuthorize("@rbac.hasPermission('sms:flashsale:detail')")
    public Result<FlashSaleActivityResponse> getActivityDetail(@PathVariable Long activityId) {
        return Result.success(flashSaleActivityService.getActivityDetail(activityId));
    }
}
