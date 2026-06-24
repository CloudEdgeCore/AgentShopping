package com.cloudedge.platform.infrastructure.cart.service;

import com.cloudedge.platform.infrastructure.cart.dto.CartOrderItemDTO;

import java.util.List;

public interface CartOrderService {

    List<CartOrderItemDTO> listOrderItems(Long userId, List<Long> cartItemIds);

    void removeItems(Long userId, List<Long> cartItemIds);
}
