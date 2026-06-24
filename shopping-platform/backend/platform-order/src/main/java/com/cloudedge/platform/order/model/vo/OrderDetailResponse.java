package com.cloudedge.platform.order.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class OrderDetailResponse {

    private String orderNo;
    private Integer status;
    private Integer totalQuantity;
    private BigDecimal totalAmount;
    private BigDecimal promotionAmount;
    private BigDecimal couponAmount;
    private BigDecimal payableAmount;
    private Long couponUserId;
    private String couponName;
    private String receiverName;
    private String receiverMobile;
    private String provinceName;
    private String cityName;
    private String districtName;
    private String detailAddress;
    private String postalCode;
    private String remark;
    private String cancelReason;
    private LocalDateTime payTime;
    private LocalDateTime cancelTime;
    private LocalDateTime createTime;
    private List<OrderItemResponse> items;
}
