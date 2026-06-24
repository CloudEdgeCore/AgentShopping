package com.cloudedge.platform.cart.controller;

import com.cloudedge.platform.cart.model.dto.CartAddRequest;
import com.cloudedge.platform.cart.model.dto.CartCheckedRequest;
import com.cloudedge.platform.cart.model.dto.CartUpdateQuantityRequest;
import com.cloudedge.platform.cart.model.vo.CartListResponse;
import com.cloudedge.platform.cart.service.CartService;
import com.cloudedge.platform.response.Result;
import com.cloudedge.platform.cart.service.impl.CartServiceImpl;
import com.cloudedge.platform.cart.model.vo.CartItemResponse;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/cart/items")
public class CartController {

    @Autowired
    private CartService cartService;

    @PostMapping
    public Result<CartItemResponse> addItem(@Valid @RequestBody CartAddRequest request){
        return Result.success(cartService.addItem(request));
    }

    @GetMapping
    public Result<CartListResponse> listCurrentUserCart(){
        return Result.success(cartService.listCurrentUserCart());
    }

    @PutMapping("/{cartItemId}/quantity")
    public Result<CartItemResponse> updateQuantity(@PathVariable Long cartItemId,
                                                   @Valid @RequestBody CartUpdateQuantityRequest request){
        return Result.success(cartService.updateQuantity(cartItemId, request));
    }

    @PutMapping("/{cartItemId}/checked")
    public Result<CartItemResponse> updateChecked(@PathVariable Long cartItemId,
                                                  @Valid @RequestBody CartCheckedRequest request){
        return Result.success(cartService.updateChecked(cartItemId, request));
    }

    @DeleteMapping("/{cartItemId}")
    public Result<Void> removeItem(@PathVariable Long cartItemId){
        cartService.removeItem(cartItemId);
        return Result.success();
    }

    @DeleteMapping("/clear")
    public Result<Void> clearCart(){
        cartService.clearCart();
        return Result.success();
    }
}
