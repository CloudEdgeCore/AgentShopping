package com.cloudedge.platform.product.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("pms_spu")
public class ProductSpuDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private Long categoryId;
    private Long brandId;
    private String spuName;
    private String subtitle;
    private String coverImage;
    private String albumImages;
    private String detail;
    private Integer publishStatus;
    private Integer sort;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
