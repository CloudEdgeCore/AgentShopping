package com.cloudedge.platform.inventory.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.cloudedge.platform.inventory.entity.SkuStockDO;
import com.cloudedge.platform.inventory.model.vo.StockPageItemResponse;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface SkuStockMapper extends BaseMapper<SkuStockDO> {

    @Select("""
            <script>
            SELECT
                s.sku_id AS skuId,
                spu.spu_name AS spuName,
                sku.sku_name AS skuName,
                s.total_stock AS stock,
                s.total_stock AS totalStock,
                s.available_stock AS availableStock,
                s.locked_stock AS lockedStock,
                s.status AS status
            FROM wms_sku_stock s
            INNER JOIN pms_sku sku ON sku.id = s.sku_id AND sku.deleted = 0
            INNER JOIN pms_spu spu ON spu.id = sku.spu_id AND spu.deleted = 0
            <where>
                <if test="keyword != null and keyword != ''">
                    (
                        CAST(s.sku_id AS CHAR) LIKE CONCAT('%', #{keyword}, '%')
                        OR sku.sku_name LIKE CONCAT('%', #{keyword}, '%')
                        OR spu.spu_name LIKE CONCAT('%', #{keyword}, '%')
                    )
                </if>
            </where>
            ORDER BY s.update_time DESC, s.id DESC
            </script>
            """)
    IPage<StockPageItemResponse> selectAdminStockPage(Page<StockPageItemResponse> page,
                                                       @Param("keyword") String keyword);
}
