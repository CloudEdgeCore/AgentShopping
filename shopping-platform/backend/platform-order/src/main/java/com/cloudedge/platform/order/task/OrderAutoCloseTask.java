package com.cloudedge.platform.order.task;

import com.cloudedge.platform.order.service.OrderService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class OrderAutoCloseTask {

    private static final Logger log = LoggerFactory.getLogger(OrderAutoCloseTask.class);

    private final OrderService orderService;

    public OrderAutoCloseTask(OrderService orderService) {
        this.orderService = orderService;
    }

    @Scheduled(initialDelay = 60000, fixedDelay = 60000)
    public void closeExpiredOrders() {
        int closedCount = orderService.closeExpiredOrders();
        if (closedCount > 0) {
            log.info("Auto closed {} expired orders", closedCount);
        }
    }
}
