package com.cloudedge.platform.inventory.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("wms_stock_lock_record")
public class StockLockRecordDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private String orderNo;
    private String bizType;
    private Long skuId;
    private Integer lockQuantity;
    private Integer status;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
