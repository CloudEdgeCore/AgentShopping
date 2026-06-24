package com.cloudedge.platform.user.service;

import com.cloudedge.platform.user.model.dto.UserAddressSaveRequest;
import com.cloudedge.platform.user.model.vo.UserAddressResponse;
import jakarta.validation.Valid;

import java.util.List;

public interface UserAddressService {
    List<UserAddressResponse> listCurrentUserAddresses();

    UserAddressResponse createCurrentUserAddress(@Valid UserAddressSaveRequest response);

    UserAddressResponse updateCurrentUserAddress(Long addressId, @Valid UserAddressSaveRequest request);

    void deleteCurrentUserAddress(Long addressId);

    void setDefaultAddress(Long addressId);
}
