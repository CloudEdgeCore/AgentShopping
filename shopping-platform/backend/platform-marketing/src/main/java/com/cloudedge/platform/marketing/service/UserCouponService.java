package com.cloudedge.platform.marketing.service;

import com.cloudedge.platform.marketing.model.dto.UserCouponPageQueryRequest;
import com.cloudedge.platform.marketing.model.vo.AvailableCouponResponse;
import com.cloudedge.platform.marketing.model.vo.PageResponse;
import com.cloudedge.platform.marketing.model.vo.UserCouponResponse;

import java.util.List;

public interface UserCouponService {

    UserCouponResponse claimCoupon(Long templateId);

    PageResponse<UserCouponResponse> pageCurrentUserCoupons(UserCouponPageQueryRequest request);

    List<AvailableCouponResponse> listAvailableCoupons();
}
