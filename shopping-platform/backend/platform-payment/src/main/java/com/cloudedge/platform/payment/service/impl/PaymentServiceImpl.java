package com.cloudedge.platform.payment.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.infrastructure.payment.service.PaymentOrderService;
import com.cloudedge.platform.order.entity.OrderDO;
import com.cloudedge.platform.order.enums.OrderStatusEnum;
import com.cloudedge.platform.order.mapper.OrderMapper;
import com.cloudedge.platform.order.service.OrderService;
import com.cloudedge.platform.payment.entity.PaymentTransactionDO;
import com.cloudedge.platform.payment.enums.PaymentChannelEnum;
import com.cloudedge.platform.payment.enums.PaymentStatusEnum;
import com.cloudedge.platform.payment.exception.PaymentErrorCode;
import com.cloudedge.platform.payment.mapper.PaymentTransactionMapper;
import com.cloudedge.platform.payment.model.dto.PaymentCreateRequest;
import com.cloudedge.platform.payment.model.vo.PaymentCreateResponse;
import com.cloudedge.platform.payment.model.vo.PaymentDetailResponse;
import com.cloudedge.platform.payment.service.PaymentService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.ThreadLocalRandom;

import static net.logstash.logback.argument.StructuredArguments.kv;

@Service
public class PaymentServiceImpl implements PaymentService, PaymentOrderService {

    private static final Logger log = LoggerFactory.getLogger(PaymentServiceImpl.class);
    private static final String SUBJECT_PREFIX = "Mock payment for order ";
    private static final DateTimeFormatter PAYMENT_NO_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS");

    @Autowired
    private PaymentTransactionMapper paymentTransactionMapper;

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private OrderService orderService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public PaymentCreateResponse createMockPayment(PaymentCreateRequest request) {
        Long userId = requireCurrentUserId();
        OrderDO orderDO = getCurrentUserOrderOrThrow(userId, request.getOrderNo());
        if (!OrderStatusEnum.PENDING_PAYMENT.getCode().equals(orderDO.getStatus())) {
            throw new BizException(PaymentErrorCode.ORDER_NOT_PAYABLE);
        }

        PaymentTransactionDO existing = getPaymentByOrderNo(userId, orderDO.getOrderNo());
        if (existing != null) {
            return buildCreateResponse(existing);
        }

        PaymentTransactionDO paymentDO = new PaymentTransactionDO();
        paymentDO.setPaymentNo(generatePaymentNo());
        paymentDO.setOrderNo(orderDO.getOrderNo());
        paymentDO.setUserId(userId);
        paymentDO.setPayChannel(PaymentChannelEnum.MOCK.getCode());
        paymentDO.setPayStatus(PaymentStatusEnum.UNPAID.getCode());
        paymentDO.setAmount(safeAmount(orderDO.getPayableAmount()));
        paymentDO.setSubject(SUBJECT_PREFIX + orderDO.getOrderNo());
        paymentDO.setDeleted(0);
        paymentTransactionMapper.insert(paymentDO);

        log.info("Mock payment created",
                kv("paymentNo", paymentDO.getPaymentNo()),
                kv("orderNo", paymentDO.getOrderNo()),
                kv("userId", userId),
                kv("amount", paymentDO.getAmount()));

        return buildCreateResponse(paymentDO);
    }

    @Override
    public PaymentDetailResponse getPaymentDetail(String paymentNo) {
        Long userId = requireCurrentUserId();
        return buildDetailResponse(getPaymentOrThrow(userId, paymentNo));
    }

    @Override
    public PaymentDetailResponse getPaymentByOrderNo(String orderNo) {
        Long userId = requireCurrentUserId();
        PaymentTransactionDO paymentDO = getPaymentByOrderNo(userId, orderNo);
        if (paymentDO == null) {
            throw new BizException(PaymentErrorCode.PAYMENT_NOT_FOUND);
        }
        return buildDetailResponse(paymentDO);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public PaymentDetailResponse mockPaySuccess(String paymentNo) {
        Long userId = requireCurrentUserId();
        PaymentTransactionDO paymentDO = getPaymentOrThrow(userId, paymentNo);

        if (PaymentStatusEnum.SUCCESS.getCode().equals(paymentDO.getPayStatus())) {
            return buildDetailResponse(paymentDO);
        }
        if (!PaymentStatusEnum.UNPAID.getCode().equals(paymentDO.getPayStatus())) {
            throw new BizException(PaymentErrorCode.PAYMENT_STATUS_INVALID);
        }

        orderService.mockPaySuccess(paymentDO.getOrderNo());

        paymentDO.setPayStatus(PaymentStatusEnum.SUCCESS.getCode());
        paymentDO.setSuccessTime(LocalDateTime.now());
        paymentTransactionMapper.updateById(paymentDO);

        log.info("Mock payment completed",
                kv("paymentNo", paymentDO.getPaymentNo()),
                kv("orderNo", paymentDO.getOrderNo()),
                kv("userId", userId),
                kv("amount", paymentDO.getAmount()));
        return buildDetailResponse(paymentDO);
    }

    @Override
    public void closeUnpaidPaymentByOrderNo(String orderNo, String closeReason) {
        PaymentTransactionDO paymentDO = paymentTransactionMapper.selectOne(Wrappers.<PaymentTransactionDO>lambdaQuery()
                .eq(PaymentTransactionDO::getOrderNo, orderNo)
                .eq(PaymentTransactionDO::getPayStatus, PaymentStatusEnum.UNPAID.getCode())
                .last("limit 1"));
        if (paymentDO == null) {
            return;
        }

        PaymentTransactionDO updateDO = new PaymentTransactionDO();
        updateDO.setId(paymentDO.getId());
        updateDO.setPayStatus(PaymentStatusEnum.CLOSED.getCode());
        updateDO.setCloseReason(trimToNull(closeReason));
        updateDO.setCloseTime(LocalDateTime.now());
        paymentTransactionMapper.updateById(updateDO);

        log.info("Unpaid payment closed",
                kv("paymentNo", paymentDO.getPaymentNo()),
                kv("orderNo", paymentDO.getOrderNo()),
                kv("reason", closeReason));
    }

    private PaymentTransactionDO getPaymentOrThrow(Long userId, String paymentNo) {
        PaymentTransactionDO paymentDO = paymentTransactionMapper.selectOne(Wrappers.<PaymentTransactionDO>lambdaQuery()
                .eq(PaymentTransactionDO::getPaymentNo, paymentNo)
                .eq(PaymentTransactionDO::getUserId, userId)
                .last("limit 1"));
        if (paymentDO == null) {
            throw new BizException(PaymentErrorCode.PAYMENT_NOT_FOUND);
        }
        return paymentDO;
    }

    private PaymentTransactionDO getPaymentByOrderNo(Long userId, String orderNo) {
        return paymentTransactionMapper.selectOne(Wrappers.<PaymentTransactionDO>lambdaQuery()
                .eq(PaymentTransactionDO::getOrderNo, orderNo)
                .eq(PaymentTransactionDO::getUserId, userId)
                .last("limit 1"));
    }

    private OrderDO getCurrentUserOrderOrThrow(Long userId, String orderNo) {
        OrderDO orderDO = orderMapper.selectOne(Wrappers.<OrderDO>lambdaQuery()
                .eq(OrderDO::getOrderNo, orderNo)
                .eq(OrderDO::getUserId, userId)
                .last("limit 1"));
        if (orderDO == null) {
            throw new BizException(PaymentErrorCode.ORDER_NOT_FOUND);
        }
        return orderDO;
    }

    private PaymentCreateResponse buildCreateResponse(PaymentTransactionDO paymentDO) {
        return PaymentCreateResponse.builder()
                .paymentNo(paymentDO.getPaymentNo())
                .orderNo(paymentDO.getOrderNo())
                .payChannel(paymentDO.getPayChannel())
                .payStatus(paymentDO.getPayStatus())
                .amount(paymentDO.getAmount())
                .subject(paymentDO.getSubject())
                .mockPayUrl("/payments/" + paymentDO.getPaymentNo() + "/success")
                .build();
    }

    private PaymentDetailResponse buildDetailResponse(PaymentTransactionDO paymentDO) {
        return PaymentDetailResponse.builder()
                .paymentNo(paymentDO.getPaymentNo())
                .orderNo(paymentDO.getOrderNo())
                .payChannel(paymentDO.getPayChannel())
                .payStatus(paymentDO.getPayStatus())
                .amount(paymentDO.getAmount())
                .subject(paymentDO.getSubject())
                .successTime(paymentDO.getSuccessTime())
                .closeTime(paymentDO.getCloseTime())
                .closeReason(paymentDO.getCloseReason())
                .createTime(paymentDO.getCreateTime())
                .build();
    }

    private Long requireCurrentUserId() {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BizException(GlobalErrorCode.UNAUTHORIZED);
        }
        return userId;
    }

    private String generatePaymentNo() {
        return "PAY"
                + LocalDateTime.now().format(PAYMENT_NO_FORMATTER)
                + ThreadLocalRandom.current().nextInt(1000, 9999);
    }

    private BigDecimal safeAmount(BigDecimal amount) {
        return amount == null ? BigDecimal.ZERO : amount;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
