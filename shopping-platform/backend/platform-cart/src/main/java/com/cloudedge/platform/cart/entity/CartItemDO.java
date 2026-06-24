package com.cloudedge.platform.cart.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("cart_item")
public class CartItemDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private Long userId;
    private Long skuId;
    private Long spuId;
    private String spuName;
    private String skuName;
    private String skuImage;
    private String skuAttrText;
    private BigDecimal salePrice;
    private Integer quantity;
    private Integer checked;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
