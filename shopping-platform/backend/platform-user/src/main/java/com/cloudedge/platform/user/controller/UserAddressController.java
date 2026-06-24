package com.cloudedge.platform.user.controller;

import com.cloudedge.platform.response.Result;
import com.cloudedge.platform.user.model.dto.UserAddressSaveRequest;
import com.cloudedge.platform.user.model.vo.UserAddressResponse;
import com.cloudedge.platform.user.service.impl.UserAddressServiceImpl;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/user/address")
public class UserAddressController {
    @Autowired private UserAddressServiceImpl userAddressService;

    @GetMapping("/list")
    public Result<List<UserAddressResponse>> listCurrentUserAddresses(){
        return Result.success(userAddressService.listCurrentUserAddresses());
    }

    @PostMapping
    public Result<UserAddressResponse> createCurrentUserAddress(@Valid @RequestBody UserAddressSaveRequest request){
        return Result.success(userAddressService.createCurrentUserAddress(request));
    }

    @PutMapping("/{addressId}")
    public Result<UserAddressResponse> updateCurrentUserAddress(@PathVariable Long addressId,
                                                                @Valid @RequestBody UserAddressSaveRequest request){
        return Result.success(userAddressService.updateCurrentUserAddress(addressId, request));
    }

    @DeleteMapping("/{addressId}")
    public Result<Void> deleteCurrentUserAddress(@PathVariable Long addressId){
        userAddressService.deleteCurrentUserAddress(addressId);
        return Result.success();
    }

    @PutMapping("/{addressId}/default")
    public Result<Void> setDefaultAddress(@PathVariable Long addressId){
        userAddressService.setDefaultAddress(addressId);
        return Result.success();
    }
}
