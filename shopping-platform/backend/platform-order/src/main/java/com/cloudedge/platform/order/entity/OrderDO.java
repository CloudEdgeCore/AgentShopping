package com.cloudedge.platform.order.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("oms_order")
public class OrderDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private String orderNo;
    private Long userId;
    private Long addressId;
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

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
