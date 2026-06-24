package com.cloudedge.platform.order.model.vo;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class OrderSubmitResponse {

    private String orderNo;
    private Integer status;
    private BigDecimal payableAmount;
}
