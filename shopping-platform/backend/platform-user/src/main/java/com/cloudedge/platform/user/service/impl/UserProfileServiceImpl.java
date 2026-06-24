package com.cloudedge.platform.user.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.user.entity.UserDO;
import com.cloudedge.platform.user.exception.UserErrorCode;
import com.cloudedge.platform.user.mapper.UserMapper;
import com.cloudedge.platform.user.model.dto.UpdateProfileRequest;
import com.cloudedge.platform.user.model.vo.UserInfoResponse;
import com.cloudedge.platform.user.service.UserProfileService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class UserProfileServiceImpl implements UserProfileService {

    @Autowired private UserMapper userMapper;

    /**
     * 获取当前用户信息
     * @return UserInfoResponse
     */
    @Override
    public UserInfoResponse getCurrentProfile() {
        return buildUserInfo(getCurrentUserEntity());
    }

    /**
     * 更新用户信息
     * @param request UpdateProfileRequest
     * @return UserInfoResponse
     */
    @Transactional(rollbackFor = Exception.class)
    @Override
    public UserInfoResponse updateCurrentProfile(UpdateProfileRequest request) {
        Long userId = requireCurrentUserId();
        UserDO currentUser = getCurrentUserEntity();

        if (StringUtils.hasText(request.getMobile()) && existsByMobile(request.getMobile().trim(), userId)) {
            throw new BizException(UserErrorCode.MOBILE_ALREADY_EXISTS);
        }

        if (StringUtils.hasText(request.getEmail()) && existsByEmail(request.getEmail().trim(), userId)) {
            throw new BizException(UserErrorCode.EMAIL_ALREADY_EXISTS);
        }

        var updateWrapper = Wrappers.<UserDO>lambdaUpdate()
                .eq(UserDO::getId, userId)
                .eq(UserDO::getDeleted, 0);

        boolean needUpdate = false;
        if (StringUtils.hasText(request.getNickname())) {
            updateWrapper.set(UserDO::getNickname, request.getNickname().trim());
            needUpdate = true;
        }

        if (StringUtils.hasText(request.getMobile())) {
            updateWrapper.set(UserDO::getMobile, request.getMobile().trim());
            needUpdate = true;
        }

        if (StringUtils.hasText(request.getEmail())) {
            updateWrapper.set(UserDO::getEmail, request.getEmail().trim());
            needUpdate = true;
        }

        if (StringUtils.hasText(request.getAvatarUrl())) {
            updateWrapper.set(UserDO::getAvatarUrl, request.getAvatarUrl().trim());
            needUpdate = true;
        }

        if (request.getGender() != null) {
            updateWrapper.set(UserDO::getGender, request.getGender());
            needUpdate = true;
        }

        if (!needUpdate) {
            return buildUserInfo(currentUser);
        }

        userMapper.update(null, updateWrapper);
        return buildUserInfo(getCurrentUserEntity());
    }

    private boolean existsByEmail(String email, Long userId) {
        LambdaQueryWrapper<UserDO> wrapper = Wrappers.<UserDO>lambdaQuery()
                .eq(UserDO::getEmail, email)
                .eq(UserDO::getDeleted, 0);

        if (userId != null) wrapper.ne(UserDO::getId, userId);
        Long count = userMapper.selectCount(wrapper);
        return count != null && count > 0;
    }

    private boolean existsByMobile(String mobile, Long userId) {
        LambdaQueryWrapper<UserDO> wrapper = Wrappers.<UserDO>lambdaQuery()
                .eq(UserDO::getMobile, mobile)
                .eq(UserDO::getDeleted, 0);
        if (userId != null) wrapper.ne(UserDO::getId, userId);

        Long count = userMapper.selectCount(wrapper);
        return count != null && count > 0;
    }

    private UserInfoResponse buildUserInfo(UserDO currentUser) {
        return UserInfoResponse.builder()
                .userId(currentUser.getId())
                .username(currentUser.getUsername())
                .nickname(currentUser.getNickname())
                .userType(currentUser.getUserType())
                .mobile(currentUser.getMobile())
                .email(currentUser.getEmail())
                .avatarUrl(currentUser.getAvatarUrl())
                .gender(currentUser.getGender())
                .build();
    }

    private UserDO getCurrentUserEntity() {
        Long userId = requireCurrentUserId();
        UserDO user = userMapper.selectById(userId);
        if (user == null || Integer.valueOf(1).equals(user.getDeleted())) throw new BizException(UserErrorCode.USER_NOT_FOUND);
        return user;
    }

    private Long requireCurrentUserId() {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BizException(GlobalErrorCode.UNAUTHORIZED);
        }
        return userId;
    }
}
