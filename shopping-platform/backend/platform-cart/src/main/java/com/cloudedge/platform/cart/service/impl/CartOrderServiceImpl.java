package com.cloudedge.platform.cart.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.cart.entity.CartItemDO;
import com.cloudedge.platform.cart.mapper.CartItemMapper;
import com.cloudedge.platform.infrastructure.cart.dto.CartOrderItemDTO;
import com.cloudedge.platform.infrastructure.cart.service.CartOrderService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;

@Service
public class CartOrderServiceImpl implements CartOrderService {

    @Autowired
    private CartItemMapper cartItemMapper;

    @Override
    public List<CartOrderItemDTO> listOrderItems(Long userId, List<Long> cartItemIds) {
        if (userId == null || cartItemIds == null || cartItemIds.isEmpty()) {
            return Collections.emptyList();
        }

        return cartItemMapper.selectList(Wrappers.<CartItemDO>lambdaQuery()
                        .eq(CartItemDO::getUserId, userId)
                        .eq(CartItemDO::getChecked, 1)
                        .in(CartItemDO::getId, cartItemIds)
                        .orderByAsc(CartItemDO::getId))
                .stream()
                .map(item -> CartOrderItemDTO.builder()
                        .cartItemId(item.getId())
                        .skuId(item.getSkuId())
                        .quantity(item.getQuantity())
                        .build())
                .toList();
    }

    @Override
    public void removeItems(Long userId, List<Long> cartItemIds) {
        if (userId == null || cartItemIds == null || cartItemIds.isEmpty()) {
            return;
        }

        cartItemMapper.delete(Wrappers.<CartItemDO>lambdaQuery()
                .eq(CartItemDO::getUserId, userId)
                .in(CartItemDO::getId, cartItemIds));
    }
}
