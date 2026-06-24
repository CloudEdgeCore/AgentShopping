package com.cloudedge.platform.cart.service;

import com.cloudedge.platform.cart.model.dto.CartAddRequest;
import com.cloudedge.platform.cart.model.dto.CartCheckedRequest;
import com.cloudedge.platform.cart.model.dto.CartUpdateQuantityRequest;
import com.cloudedge.platform.cart.model.vo.CartItemResponse;
import com.cloudedge.platform.cart.model.vo.CartListResponse;
import jakarta.validation.Valid;

public interface CartService {
    CartItemResponse addItem(@Valid CartAddRequest request);

    CartListResponse listCurrentUserCart();

    CartItemResponse updateQuantity(Long cartItemId, CartUpdateQuantityRequest request);

    CartItemResponse updateChecked(Long cartItemId, @Valid CartCheckedRequest request);

    void removeItem(Long cartItemId);

    void clearCart();
}
