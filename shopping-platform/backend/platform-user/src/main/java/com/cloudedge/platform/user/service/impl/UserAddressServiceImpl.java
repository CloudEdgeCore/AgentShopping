package com.cloudedge.platform.user.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.user.entity.UserAddressDO;
import com.cloudedge.platform.user.enums.UserStatusEnum;
import com.cloudedge.platform.user.exception.UserErrorCode;
import com.cloudedge.platform.user.mapper.UserAddressMapper;
import com.cloudedge.platform.user.model.dto.UserAddressSaveRequest;
import com.cloudedge.platform.user.model.vo.UserAddressResponse;
import com.cloudedge.platform.user.service.UserAddressService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class UserAddressServiceImpl implements UserAddressService {

    @Autowired private UserAddressMapper userAddressMapper;

    @Override
    public List<UserAddressResponse> listCurrentUserAddresses() {
        Long userId = requireCurrentUserId();
        List<UserAddressDO> addressDOList = userAddressMapper.selectList(Wrappers.<UserAddressDO>lambdaQuery()
                .eq(UserAddressDO::getUserId, userId)
                .eq(UserAddressDO::getDeleted, 0)
                .orderByDesc(UserAddressDO::getIsDefault)
                .orderByDesc(UserAddressDO::getUpdateTime)
                .orderByDesc(UserAddressDO::getId));

        return addressDOList.stream().map(this::buildResponse).toList();
    }

    /**
     * 为当前用户创建收货地址
     * @param request UserAddressSaveRequest
     * @return UserAddressResponse
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserAddressResponse createCurrentUserAddress(@Valid UserAddressSaveRequest request) {
        Long userId = requireCurrentUserId();
        boolean setDefault = Boolean.TRUE.equals(request.getDefaultAddress()) || !hasAddress(userId);

        if (setDefault) clearDefaultAddress(userId);

        UserAddressDO addressDO = new UserAddressDO();
        addressDO.setUserId(userId);
        addressDO.setReceiverName(request.getReceiverName().trim());
        addressDO.setReceiverMobile(request.getReceiverMobile().trim());
        addressDO.setProvinceCode(trimToNull(request.getProvinceCode()));
        addressDO.setProvinceName(trimToNull(request.getProvinceName()));
        addressDO.setCityCode(trimToNull(request.getCityCode()));
        addressDO.setCityName(trimToNull(request.getCityName()));
        addressDO.setDistrictCode(trimToNull(request.getDistrictCode()));
        addressDO.setDistrictName(trimToNull(request.getDistrictName()));
        addressDO.setDetailAddress(request.getDetailAddress().trim());
        addressDO.setPostalCode(trimToNull(request.getPostalCode()));
        addressDO.setIsDefault(setDefault ? 1 : 0);
        addressDO.setStatus(UserStatusEnum.ENABLED.getCode());
        addressDO.setDeleted(0);

        userAddressMapper.insert(addressDO);
        return buildResponse(addressDO);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserAddressResponse updateCurrentUserAddress(Long addressId, UserAddressSaveRequest request) {
        Long userId = requireCurrentUserId();
        UserAddressDO currentAddress = getCurrentUserAddress(addressId, userId);
        if (Boolean.TRUE.equals(request.getDefaultAddress())) clearDefaultAddress(userId);

        var updateWrapper = Wrappers.<UserAddressDO>lambdaUpdate()
                .eq(UserAddressDO::getId, addressId)
                .eq(UserAddressDO::getUserId, userId)
                .eq(UserAddressDO::getDeleted, 0)
                .set(UserAddressDO::getReceiverName, request.getReceiverName().trim())
                .set(UserAddressDO::getReceiverMobile, request.getReceiverMobile().trim())
                .set(UserAddressDO::getProvinceCode, trimToNull(request.getProvinceCode()))
                .set(UserAddressDO::getProvinceName, trimToNull(request.getProvinceName()))
                .set(UserAddressDO::getCityCode, trimToNull(request.getCityCode()))
                .set(UserAddressDO::getCityName, trimToNull(request.getCityName()))
                .set(UserAddressDO::getDistrictCode, trimToNull(request.getDistrictCode()))
                .set(UserAddressDO::getDistrictName, trimToNull(request.getDistrictName()))
                .set(UserAddressDO::getDetailAddress, request.getDetailAddress().trim())
                .set(UserAddressDO::getPostalCode, trimToNull(request.getPostalCode()));

        if (request.getDefaultAddress() != null) {
            updateWrapper.set(UserAddressDO::getIsDefault, Boolean.TRUE.equals(request.getDefaultAddress()) ? 1 : 0);
        }

        userAddressMapper.update(null, updateWrapper);
        UserAddressDO updatedAddress = userAddressMapper.selectById(addressId);
        if (updatedAddress == null) throw new BizException(UserErrorCode.ADDRESS_NOT_FOUND);

        if (Boolean.FALSE.equals(request.getDefaultAddress()) && Integer.valueOf(1).equals(currentAddress.getIsDefault())) {
            ensureOneDefaultAddress(userId);
            updatedAddress = userAddressMapper.selectById(addressId);
        }
        return buildResponse(updatedAddress);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteCurrentUserAddress(Long addressId) {
        Long userId = requireCurrentUserId();
        UserAddressDO currentUserAddress = getCurrentUserAddress(addressId, userId);

        UserAddressDO deleteAddress = new UserAddressDO();
        deleteAddress.setId(addressId);
        deleteAddress.setDeleted(1);
        deleteAddress.setIsDefault(0);
        userAddressMapper.updateById(deleteAddress);
        if (Integer.valueOf(1).equals(currentUserAddress.getIsDefault())) {
            ensureOneDefaultAddress(userId);
        }
    }

    @Transactional(rollbackFor = Exception.class)
    @Override
    public void setDefaultAddress(Long addressId) {
        Long userId = requireCurrentUserId();
        getCurrentUserAddress(addressId, userId);

        clearDefaultAddress(userId);

        UserAddressDO updateAddress = new UserAddressDO();
        updateAddress.setId(addressId);
        updateAddress.setIsDefault(1);
        userAddressMapper.updateById(updateAddress);
    }

    private void ensureOneDefaultAddress(Long userId) {
        Long count = userAddressMapper.selectCount(Wrappers.<UserAddressDO>lambdaQuery()
                .eq(UserAddressDO::getUserId, userId)
                .eq(UserAddressDO::getDeleted, 0)
                .eq(UserAddressDO::getIsDefault, 1));
        if (count != null && count > 0) return;

        UserAddressDO fallbackAddress = userAddressMapper.selectOne(Wrappers.<UserAddressDO>lambdaQuery()
                .eq(UserAddressDO::getUserId, userId)
                .eq(UserAddressDO::getDeleted, 0)
                .orderByDesc(UserAddressDO::getUpdateTime)
                .orderByDesc(UserAddressDO::getId)
                .last("limit 1"));
        if (fallbackAddress == null) return;

        userAddressMapper.update(null, Wrappers.<UserAddressDO>lambdaUpdate()
                .eq(UserAddressDO::getId, fallbackAddress.getId())
                .eq(UserAddressDO::getUserId, userId)
                .eq(UserAddressDO::getDeleted, 0)
                .set(UserAddressDO::getIsDefault, 1));
    }

    private UserAddressDO getCurrentUserAddress(Long addressId, Long userId) {
        UserAddressDO addressDO = userAddressMapper.selectById(addressId);
        if (addressDO == null || Integer.valueOf(1).equals(addressDO.getDeleted()) || !userId.equals(addressDO.getUserId())) {
            throw new BizException(UserErrorCode.ADDRESS_NOT_FOUND);
        }
        return addressDO;
    }

    private String trimToNull(String value){
        if (value == null) return null;
        return value.trim().isEmpty() ? null : value.trim();
    }

    private void clearDefaultAddress(Long userId) {
        userAddressMapper.update(null, Wrappers.<UserAddressDO>lambdaUpdate()
                .eq(UserAddressDO::getUserId, userId)
                .eq(UserAddressDO::getDeleted, 0)
                .eq(UserAddressDO::getIsDefault, 1)
                .set(UserAddressDO::getIsDefault, 0));
    }

    private boolean hasAddress(Long userId) {
        Long count = userAddressMapper.selectCount(Wrappers.<UserAddressDO>lambdaQuery()
                .eq(UserAddressDO::getUserId, userId)
                .eq(UserAddressDO::getDeleted, 0));
        return count != null && count > 0;
    }

    private UserAddressResponse buildResponse(UserAddressDO userAddressDO) {
        return UserAddressResponse.builder()
                .id(userAddressDO.getId())
                .receiverName(userAddressDO.getReceiverName())
                .receiverMobile(userAddressDO.getReceiverMobile())
                .provinceCode(userAddressDO.getProvinceCode())
                .provinceName(userAddressDO.getProvinceName())
                .cityCode(userAddressDO.getCityCode())
                .cityName(userAddressDO.getCityName())
                .districtCode(userAddressDO.getDistrictCode())
                .districtName(userAddressDO.getDistrictName())
                .detailAddress(userAddressDO.getDetailAddress())
                .postalCode(userAddressDO.getPostalCode())
                .defaultAddress(Integer.valueOf(1).equals(userAddressDO.getIsDefault()))
                .build();
    }

    private Long requireCurrentUserId() {
        Long userId = UserContext.getUserId();
        if (userId == null) throw new BizException(GlobalErrorCode.UNAUTHORIZED);
        return userId;
    }
}
