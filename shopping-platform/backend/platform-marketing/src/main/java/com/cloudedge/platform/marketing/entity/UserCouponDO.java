package com.cloudedge.platform.marketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("sms_user_coupon")
public class UserCouponDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private Long templateId;
    private Long userId;
    private String couponCode;
    private String couponName;
    private Integer couponType;
    private BigDecimal thresholdAmount;
    private BigDecimal discountAmount;
    private BigDecimal discountRate;
    private Integer scopeType;
    private Integer status;
    private LocalDateTime receiveTime;
    private LocalDateTime validFrom;
    private LocalDateTime validTo;
    private LocalDateTime useTime;
    private String orderNo;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
