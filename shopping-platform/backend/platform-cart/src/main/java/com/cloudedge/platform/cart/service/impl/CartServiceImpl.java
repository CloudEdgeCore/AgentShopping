package com.cloudedge.platform.cart.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.cart.exception.CartErrorCode;
import com.cloudedge.platform.cart.model.dto.CartAddRequest;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.cart.mapper.CartItemMapper;
import com.cloudedge.platform.cart.model.dto.CartCheckedRequest;
import com.cloudedge.platform.cart.model.dto.CartUpdateQuantityRequest;
import com.cloudedge.platform.infrastructure.product.dto.ProductCartSkuInfo;
import com.cloudedge.platform.cart.entity.CartItemDO;
import com.cloudedge.platform.cart.model.vo.CartListResponse;
import com.cloudedge.platform.infrastructure.product.service.ProductCartReadService;
import com.cloudedge.platform.cart.service.CartService;
import com.cloudedge.platform.cart.model.vo.CartItemResponse;
import jakarta.validation.constraints.NotNull;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Service
public class CartServiceImpl implements CartService {

    @Autowired
    private CartItemMapper cartItemMapper;

    @Autowired
    private ProductCartReadService productCartReadService;

    @Override
    public CartItemResponse addItem(CartAddRequest request) {
        Long userId = requireCurrentUserId();
        ProductCartSkuInfo skuInfo = requireSaleableSku(request.getSkuId());

        CartItemDO existingItem = cartItemMapper.selectOne(Wrappers.<CartItemDO>lambdaQuery()
                .eq(CartItemDO::getUserId, userId)
                .eq(CartItemDO::getSkuId, request.getSkuId())
                .last("limit 1"));

        if (existingItem == null) {
            CartItemDO cartItemDO = new CartItemDO();
            cartItemDO.setUserId(userId);
            fillSnapshot(cartItemDO, skuInfo);
            cartItemDO.setQuantity(request.getQuantity());
            cartItemDO.setChecked(1);
            cartItemMapper.insert(cartItemDO);
            return buildItemResponse(cartItemDO, skuInfo);
        }

        fillSnapshot(existingItem, skuInfo);
        existingItem.setQuantity(existingItem.getQuantity() + request.getQuantity());
        existingItem.setChecked(1);
        cartItemMapper.updateById(existingItem);
        return buildItemResponse(existingItem, skuInfo);
    }

    @Override
    public CartListResponse listCurrentUserCart() {
        Long userId = requireCurrentUserId();
        List<CartItemDO> itemList = cartItemMapper.selectList(Wrappers.<CartItemDO>lambdaQuery()
                .eq(CartItemDO::getUserId, userId)
                .orderByDesc(CartItemDO::getUpdateTime)
                .orderByDesc(CartItemDO::getId));

        if (itemList.isEmpty()) {
            return CartListResponse.builder()
                    .items(Collections.emptyList())
                    .totalItemCount(0)
                    .checkedItemCount(0)
                    .checkedAmount(BigDecimal.ZERO)
                    .build();
        }
        List<Long> skuIds = itemList.stream().map(CartItemDO::getSkuId).distinct().toList();
        Map<Long, ProductCartSkuInfo> skuInfoMap = productCartReadService.getSaleableSkuInfoMap(skuIds);

        int totalItemCount = 0;
        int checkedItemCount = 0;
        BigDecimal checkedAmount = BigDecimal.ZERO;

        List<CartItemResponse> items = new java.util.ArrayList<>(itemList.size());
        for (CartItemDO item : itemList) {
            ProductCartSkuInfo skuInfo = skuInfoMap.get(item.getSkuId());
            CartItemResponse response = buildItemResponse(item, skuInfo);

            int quantity = item.getQuantity() == null ? 0 : item.getQuantity();
            totalItemCount += quantity;

            if (Objects.equals(item.getChecked(), 1) && Boolean.TRUE.equals(response.getProductAvailable())) {
                checkedItemCount += quantity;
                checkedAmount = checkedAmount.add(response.getLineAmount());
            }

            items.add(response);
        }
        return CartListResponse.builder()
                .items(items)
                .totalItemCount(totalItemCount)
                .checkedItemCount(checkedItemCount)
                .checkedAmount(checkedAmount)
                .build();
    }

    @Override
    public CartItemResponse updateQuantity(Long cartItemId, CartUpdateQuantityRequest request) {
        Long userId = requireCurrentUserId();
        CartItemDO cartItemDO = getCartItemOrThrow(userId, cartItemId);
        ProductCartSkuInfo skuInfo = requireSaleableSku(cartItemDO.getSkuId());

        fillSnapshot(cartItemDO, skuInfo);
        cartItemDO.setQuantity(request.getQuantity());
        cartItemMapper.updateById(cartItemDO);
        return buildItemResponse(cartItemDO, skuInfo);
    }

    /**
     * 更新某一条购物车项的勾选状态
     * @param cartItemId Long
     * @param request CartCheckedRequest
     * @return CartItemResponse
     */
    @Override
    public CartItemResponse updateChecked(Long cartItemId, CartCheckedRequest request) {
        Long userId = requireCurrentUserId();
        CartItemDO cartItemDO = getCartItemOrThrow(userId, cartItemId);

        cartItemDO.setChecked(Boolean.TRUE.equals(request.getChecked()) ? 1 : 0);
        cartItemMapper.updateById(cartItemDO);

        ProductCartSkuInfo skuInfo = productCartReadService.getSaleableSkuInfoBySkuId(cartItemDO.getSkuId());
        return buildItemResponse(cartItemDO, skuInfo);
    }

    @Override
    public void removeItem(Long cartItemId) {
        Long userId = requireCurrentUserId();
        int rows = cartItemMapper.delete(Wrappers.<CartItemDO>lambdaQuery()
                .eq(CartItemDO::getId, cartItemId)
                .eq(CartItemDO::getUserId, userId));
        if (rows <= 0) {
            throw new BizException(CartErrorCode.CART_ITEM_NOT_FOUND);
        }
    }

    @Override
    public void clearCart() {
        Long userId = requireCurrentUserId();
        cartItemMapper.delete(Wrappers.<CartItemDO>lambdaQuery()
                .eq(CartItemDO::getUserId, userId));
    }

    private CartItemDO getCartItemOrThrow(Long userId, Long cartItemId) {
        CartItemDO cartItemDO = cartItemMapper.selectOne(Wrappers.<CartItemDO>lambdaQuery()
                .eq(CartItemDO::getId, cartItemId)
                .eq(CartItemDO::getUserId, userId)
                .last("limit 1"));

        if (cartItemDO == null) {
            throw new BizException(CartErrorCode.CART_ITEM_NOT_FOUND);
        }
        return cartItemDO;
    }

    private CartItemResponse buildItemResponse(CartItemDO item, ProductCartSkuInfo skuInfo) {
        boolean available = skuInfo != null;
        BigDecimal snapshotPrice = safePrice(item.getSalePrice());
        BigDecimal currentPrice = available ? safePrice(skuInfo.getSalePrice()) : snapshotPrice;
        int quantity = item.getQuantity() == null ? 0 : item.getQuantity();

        return CartItemResponse.builder()
                .id(item.getId())
                .skuId(item.getSkuId())
                .skuName(item.getSkuName())
                .spuId(item.getSpuId())
                .spuName(item.getSpuName())
                .skuImage(item.getSkuImage())
                .skuAttrText(item.getSkuAttrText())
                .salePrice(snapshotPrice)
                .currentSalePrice(currentPrice)
                .quantity(quantity)
                .checked(Objects.equals(item.getChecked(), 1))
                .productAvailable(available)
                .priceChanged(available && snapshotPrice.compareTo(currentPrice) != 0)
                .lineAmount(currentPrice.multiply(BigDecimal.valueOf(quantity)))
                .build();
    }

    private BigDecimal safePrice(BigDecimal salePrice) {
        return salePrice == null ? BigDecimal.ZERO : salePrice;
    }

    private void fillSnapshot(CartItemDO cartItemDO, ProductCartSkuInfo skuInfo) {
        cartItemDO.setSkuId(skuInfo.getSkuId());
        cartItemDO.setSkuName(skuInfo.getSkuName());
        cartItemDO.setSkuAttrText(skuInfo.getSkuAttrText());
        cartItemDO.setSpuName(skuInfo.getSpuName());
        cartItemDO.setSpuId(skuInfo.getSpuId());
        cartItemDO.setSkuImage(skuInfo.getSkuImage());
        cartItemDO.setSalePrice(skuInfo.getSalePrice());
    }

    /**
     * 拿到可售卖的商品信息
     * @param skuId Long
     * @return ProductCartSkuInfo
     */
    private ProductCartSkuInfo requireSaleableSku(@NotNull(message = "skuId cannot be null") Long skuId) {
        ProductCartSkuInfo skuInfo = productCartReadService.getSaleableSkuInfoBySkuId(skuId);
        if (skuInfo == null) throw new BizException(CartErrorCode.SKU_NOT_SALEABLE);
        return skuInfo;
    }

    private Long requireCurrentUserId() {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BizException(GlobalErrorCode.UNAUTHORIZED);
        }
        return userId;
    }
}
