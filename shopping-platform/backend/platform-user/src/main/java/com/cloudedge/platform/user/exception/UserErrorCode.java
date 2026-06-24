package com.cloudedge.platform.user.exception;

import com.cloudedge.platform.exception.ErrorCode;

public enum UserErrorCode implements ErrorCode {

    USERNAME_OR_PASSWORD_ERROR("U0001", "用户名或密码错误"),
    USER_DISABLED("U0002", "用户已被禁用"),
    USER_NOT_FOUND("U0003", "用户不存在"),
    USERNAME_ALREADY_EXISTS("U0004", "用户名已存在"),
    MOBILE_ALREADY_EXISTS("U0005", "手机号已存在"),
    EMAIL_ALREADY_EXISTS("U0006", "邮箱已存在"),
    ADDRESS_NOT_FOUND("U0007", "收货地址不存在");

    private final String code;
    private final String message;

    UserErrorCode(String code, String message) {
        this.code = code;
        this.message = message;
    }

    @Override
    public String getCode() {
        return code;
    }

    @Override
    public String getMessage() {
        return message;
    }
}
