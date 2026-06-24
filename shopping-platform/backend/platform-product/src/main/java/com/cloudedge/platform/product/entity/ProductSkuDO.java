package com.cloudedge.platform.product.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("pms_sku")
public class ProductSkuDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private Long spuId;
    private String skuCode;
    private String skuName;
    private String imageUrl;
    private BigDecimal salePrice;
    private BigDecimal marketPrice;
    private String attrText;
    private Integer isDefault;
    private Integer status;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
