package com.cloudedge.platform.cart.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cloudedge.platform.cart.entity.CartItemDO;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface CartItemMapper extends BaseMapper<CartItemDO> {
}
