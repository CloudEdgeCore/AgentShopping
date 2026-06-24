package com.cloudedge.platform.payment.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("pay_transaction")
public class PaymentTransactionDO {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private String paymentNo;
    private String orderNo;
    private Long userId;
    private Integer payChannel;
    private Integer payStatus;
    private BigDecimal amount;
    private String subject;
    private LocalDateTime successTime;
    private LocalDateTime closeTime;
    private String closeReason;

    @TableLogic
    private Integer deleted;

    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
