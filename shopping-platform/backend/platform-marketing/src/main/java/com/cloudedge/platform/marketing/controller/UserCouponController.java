package com.cloudedge.platform.marketing.controller;

import com.cloudedge.platform.marketing.model.dto.UserCouponPageQueryRequest;
import com.cloudedge.platform.marketing.model.vo.AvailableCouponResponse;
import com.cloudedge.platform.marketing.model.vo.PageResponse;
import com.cloudedge.platform.marketing.model.vo.UserCouponResponse;
import com.cloudedge.platform.marketing.service.UserCouponService;
import com.cloudedge.platform.response.Result;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/marketing/coupons")
public class UserCouponController {

    @Autowired
    private UserCouponService userCouponService;

    @PostMapping("/claim/{templateId}")
    public Result<UserCouponResponse> claimCoupon(@PathVariable Long templateId) {
        return Result.success(userCouponService.claimCoupon(templateId));
    }

    @GetMapping("/my")
    public Result<PageResponse<UserCouponResponse>> pageCurrentUserCoupons(@Valid UserCouponPageQueryRequest request) {
        return Result.success(userCouponService.pageCurrentUserCoupons(request));
    }

    @GetMapping("/available")
    public Result<List<AvailableCouponResponse>> listAvailableCoupons() {
        return Result.success(userCouponService.listAvailableCoupons());
    }
}
