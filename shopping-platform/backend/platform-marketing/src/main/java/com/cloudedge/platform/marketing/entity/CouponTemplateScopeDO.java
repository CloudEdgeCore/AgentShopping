package com.cloudedge.platform.marketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("sms_coupon_template_scope")
public class CouponTemplateScopeDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private Long templateId;
    private Integer scopeType;
    private Long scopeId;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
