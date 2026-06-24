package com.cloudedge.platform.order.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("oms_order_item")
public class OrderItemDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private Long orderId;
    private String orderNo;
    private Long skuId;
    private Long spuId;
    private String spuName;
    private String skuName;
    private String skuImage;
    private String skuAttrText;
    private BigDecimal originalPrice;
    private BigDecimal salePrice;
    private Integer quantity;
    private BigDecimal promotionAmount;
    private BigDecimal totalAmount;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
