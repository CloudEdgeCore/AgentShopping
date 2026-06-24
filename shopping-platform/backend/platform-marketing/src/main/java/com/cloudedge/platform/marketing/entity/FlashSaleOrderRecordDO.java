package com.cloudedge.platform.marketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("sms_flash_sale_order_record")
public class FlashSaleOrderRecordDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private String orderNo;
    private Long activityId;
    private Long skuId;
    private Integer quantity;
    private BigDecimal discountPrice;
    private Integer status;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
