package com.cloudedge.platform.product.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cloudedge.platform.product.entity.CategoryDO;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface CategoryMapper extends BaseMapper<CategoryDO> {
}
