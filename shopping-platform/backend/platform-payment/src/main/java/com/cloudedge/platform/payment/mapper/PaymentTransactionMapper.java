package com.cloudedge.platform.payment.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cloudedge.platform.payment.entity.PaymentTransactionDO;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface PaymentTransactionMapper extends BaseMapper<PaymentTransactionDO> {
}
