package com.cloudedge.platform.order.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cloudedge.platform.order.entity.OrderItemDO;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface OrderItemMapper extends BaseMapper<OrderItemDO> {
}
