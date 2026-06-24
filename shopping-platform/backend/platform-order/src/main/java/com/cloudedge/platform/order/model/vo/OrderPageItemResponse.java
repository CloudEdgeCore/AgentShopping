package com.cloudedge.platform.order.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Builder
public class OrderPageItemResponse {

    private String orderNo;
    private Integer status;
    private Integer totalQuantity;
    private BigDecimal payableAmount;
    private String firstSkuName;
    private String firstSkuImage;
    private LocalDateTime createTime;
}
