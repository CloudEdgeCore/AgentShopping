package com.cloudedge.platform.marketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("sms_flash_sale_sku")
public class FlashSaleSkuDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private Long activityId;
    private Long skuId;
    private BigDecimal originalPrice;
    private BigDecimal discountPrice;
    private Integer activityStock;
    private Integer lockedStock;
    private Integer perUserLimit;
    private Integer sort;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
