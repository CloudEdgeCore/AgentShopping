package com.cloudedge.platform.user.controller;

import com.cloudedge.platform.response.Result;
import com.cloudedge.platform.user.model.dto.LoginRequest;
import com.cloudedge.platform.user.model.dto.RegisterRequest;
import com.cloudedge.platform.user.model.vo.LoginResponse;
import com.cloudedge.platform.user.model.vo.UserInfoResponse;
import com.cloudedge.platform.user.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth")
public class AuthController {

    @Autowired private AuthService authService;

    @PostMapping("/register")
    public Result<UserInfoResponse> register(@Valid @RequestBody RegisterRequest request){
        return Result.success(authService.register(request));
    }

    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request,
                                       HttpServletRequest httpServletRequest) {
        return Result.success(authService.login(request, httpServletRequest.getRemoteAddr()));
    }

    @PostMapping("/logout")
    public Result<Void> logout(HttpServletRequest request) {
        authService.logout(request);
        return Result.success();
    }

    @GetMapping("/me")
    public Result<UserInfoResponse> me(){
        return Result.success(authService.getCurrentUser());
    }
}
