package com.cloudedge.platform.user.service;

import com.cloudedge.platform.user.model.dto.LoginRequest;
import com.cloudedge.platform.user.model.dto.RegisterRequest;
import com.cloudedge.platform.user.model.vo.LoginResponse;
import com.cloudedge.platform.user.model.vo.UserInfoResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;

public interface AuthService {
    LoginResponse login(@Valid LoginRequest request, String remoteAddr);

    void logout(HttpServletRequest request);

    UserInfoResponse getCurrentUser();

    UserInfoResponse register(@Valid RegisterRequest request);
}
