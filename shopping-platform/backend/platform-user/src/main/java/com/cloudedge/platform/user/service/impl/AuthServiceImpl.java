package com.cloudedge.platform.user.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.config.SecurityProperties;
import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.exception.JwtAuthenticationException;
import com.cloudedge.platform.model.LoginUser;
import com.cloudedge.platform.user.entity.UserDO;
import com.cloudedge.platform.user.enums.UserStatusEnum;
import com.cloudedge.platform.user.enums.UserTypeEnum;
import com.cloudedge.platform.user.exception.UserErrorCode;
import com.cloudedge.platform.user.mapper.UserMapper;
import com.cloudedge.platform.user.model.dto.LoginRequest;
import com.cloudedge.platform.user.model.dto.RegisterRequest;
import com.cloudedge.platform.user.model.dto.UserRbacProfile;
import com.cloudedge.platform.user.model.vo.LoginResponse;
import com.cloudedge.platform.user.model.vo.UserInfoResponse;
import com.cloudedge.platform.user.service.AuthService;
import com.cloudedge.platform.user.service.UserRbacService;
import com.cloudedge.platform.util.JwtTokenProvider;
import com.cloudedge.platform.util.TokenBlacklistService;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.Collections;

import static net.logstash.logback.argument.StructuredArguments.kv;

@Service
public class AuthServiceImpl implements AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthServiceImpl.class);

    @Autowired private UserRbacService userRbacService;

    @Autowired private PasswordEncoder passwordEncoder;

    @Autowired private UserMapper userMapper;

    @Autowired private JwtTokenProvider jwtTokenProvider;

    @Autowired private TokenBlacklistService tokenBlacklistService;

    @Autowired private SecurityProperties securityProperties;

    @Override
    public LoginResponse login(LoginRequest request, String loginIp) {
        UserDO user = userMapper.selectOne(Wrappers.<UserDO>lambdaQuery()
                .eq(UserDO::getUsername, request.getUsername())
                .eq(UserDO::getDeleted, 0)
                .last("limit 1"));

        if (user == null || !passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            log.warn("Login failed",
                    kv("username", request.getUsername()),
                    kv("loginIp", loginIp),
                    kv("reason", "bad_credentials"));
            throw new BizException(UserErrorCode.USERNAME_OR_PASSWORD_ERROR);
        }

        if (UserStatusEnum.DISABLED.getCode().equals(user.getStatus())) {
            log.warn("Login blocked",
                    kv("userId", user.getId()),
                    kv("username", user.getUsername()),
                    kv("loginIp", loginIp),
                    kv("reason", "user_disabled"));
            throw new BizException(UserErrorCode.USER_DISABLED);
        }

        UserRbacProfile rbacProfile = userRbacService.getUserRbacProfile(user.getId());
        LoginUser loginUser = buildLoginUser(user, rbacProfile);

        String accessToken = jwtTokenProvider.createAccessToken(loginUser);
        updateLoginInfo(user.getId(), loginIp);
        log.info("Login succeeded",
                kv("userId", user.getId()),
                kv("username", user.getUsername()),
                kv("userType", user.getUserType()),
                kv("loginIp", loginIp));

        return LoginResponse.builder()
                .accessToken(accessToken)
                .tokenType("Bearer")
                .expiresIn(securityProperties.getAccessTokenValiditySeconds())
                .userInfo(buildUserInfo(user, rbacProfile))
                .build();
    }

    private LoginUser buildLoginUser(UserDO user, UserRbacProfile rbacProfile) {
        return LoginUser.builder()
                .userId(user.getId())
                .userName(user.getUsername())
                .userType(user.getUserType())
                .roles(rbacProfile.getRoles())
                .permissions(rbacProfile.getPermissions())
                .build();
    }

    private UserInfoResponse buildUserInfo(UserDO user, UserRbacProfile rbacProfile) {
        return UserInfoResponse.builder()
                .userId(user.getId())
                .username(user.getUsername())
                .nickname(user.getNickname())
                .userType(user.getUserType())
                .mobile(user.getMobile())
                .email(user.getEmail())
                .avatarUrl(user.getAvatarUrl())
                .gender(user.getGender())
                .roles(rbacProfile.getRoles())
                .permissions(rbacProfile.getPermissions())
                .build();
    }

    @Override
    public void logout(HttpServletRequest request) {
        String token = jwtTokenProvider.resolveToken(request);
        if (token == null || token.isBlank()) {
            return;
        }
        try {
            long ttlSeconds = jwtTokenProvider.getRemainingValiditySeconds(token);
            if (ttlSeconds > 0) {
                tokenBlacklistService.blacklist(token, ttlSeconds);
            }
            LoginUser loginUser = UserContext.get();
            if (loginUser != null && loginUser.getUserId() != null) {
                log.info("Logout succeeded",
                        kv("userId", loginUser.getUserId()),
                        kv("username", loginUser.getUserName()));
            }
        } catch (JwtAuthenticationException ignored) {
            // Ignore invalid token on logout to keep endpoint idempotent.
        }
    }

    @Override
    public UserInfoResponse getCurrentUser() {
        LoginUser loginUser = UserContext.get();
        if (loginUser == null || loginUser.getUserId() == null) {
            throw new BizException(GlobalErrorCode.UNAUTHORIZED);
        }

        UserDO user = userMapper.selectById(loginUser.getUserId());
        if (user == null || Integer.valueOf(1).equals(user.getDeleted())) {
            throw new BizException(UserErrorCode.USER_NOT_FOUND);
        }

        UserRbacProfile rbacProfile = userRbacService.getUserRbacProfile(user.getId());
        return buildUserInfo(user, rbacProfile);
    }


    @Override
    public UserInfoResponse register(RegisterRequest request) {
        String username = request.getUsername().trim();
        String mobile = trimToNull(request.getMobile());
        String email = trimToNull(request.getEmail());
        String nickname = StringUtils.hasText(request.getNickname()) ? request.getNickname().trim() : username;
        String avatarUrl = trimToNull(request.getAvatarUrl());

        if (existsByUsername(username, null)) throw new BizException(UserErrorCode.USERNAME_ALREADY_EXISTS);

        if (StringUtils.hasText(mobile) && existsByMobile(mobile, null)) throw new BizException(UserErrorCode.MOBILE_ALREADY_EXISTS);

        if (StringUtils.hasText(email) && existsByEmail(email, null)) throw new BizException(UserErrorCode.EMAIL_ALREADY_EXISTS);

        UserDO userDO = new UserDO();
        userDO.setUsername(username);
        userDO.setMobile(mobile);
        userDO.setEmail(email);
        userDO.setNickname(nickname);
        userDO.setAvatarUrl(avatarUrl);
        userDO.setPassword(passwordEncoder.encode(request.getPassword()));
        userDO.setGender(request.getGender() == null ? 0 : request.getGender());
        userDO.setUserType(UserTypeEnum.C_END.getCode());
        userDO.setStatus(UserStatusEnum.ENABLED.getCode());
        userDO.setDeleted(0);

        userMapper.insert(userDO);
        log.info("User registered successfully",
                kv("userId", userDO.getId()),
                kv("username", userDO.getUsername()),
                kv("userType", userDO.getUserType()));
        return buildUserInfo(userDO, UserRbacProfile.builder().build());
    }

    private boolean existsByEmail(String email, Long excludeUserId) {
        LambdaQueryWrapper<UserDO> wrapper = Wrappers.<UserDO>lambdaQuery()
                .eq(UserDO::getEmail, email)
                .eq(UserDO::getDeleted, 0);
        if (excludeUserId != null) {
            wrapper.ne(UserDO::getId, excludeUserId);
        }
        Long count = userMapper.selectCount(wrapper);
        return count != null && count > 0;
    }

    private boolean existsByMobile(String mobile, Long excludeUserId) {
        LambdaQueryWrapper<UserDO> wrapper = Wrappers.<UserDO>lambdaQuery()
                .eq(UserDO::getMobile, mobile)
                .eq(UserDO::getDeleted, 0);
        if (excludeUserId != null) wrapper.ne(UserDO::getId, excludeUserId);
        Long count = userMapper.selectCount(wrapper);
        return count != null && count > 0;
    }

    private boolean existsByUsername(String username, Long excludeUserId) {
        LambdaQueryWrapper<UserDO> wrapper = Wrappers.<UserDO>lambdaQuery()
                .eq(UserDO::getUsername, username)
                .eq(UserDO::getDeleted, 0);
        if (excludeUserId != null) wrapper.ne(UserDO::getId, excludeUserId);
        Long count = userMapper.selectCount(wrapper);
        return count != null && count > 0;
    }

    private void updateLoginInfo(Long userId, String loginIp) {
        UserDO userDO = new UserDO();
        userDO.setId(userId);
        userDO.setLastLoginTime(LocalDateTime.now());
        userDO.setLastLoginIp(loginIp);
        userMapper.updateById(userDO);
    }

    private String trimToNull(String str) {
        if (str == null) return null;
        String trimmed = str.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
