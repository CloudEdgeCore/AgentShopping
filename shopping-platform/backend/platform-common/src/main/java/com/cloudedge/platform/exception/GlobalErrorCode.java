package com.cloudedge.platform.exception;

public enum GlobalErrorCode implements ErrorCode {

    SUCCESS("00000", "操作成功"),
    BAD_REQUEST("A0400", "请求参数错误"),
    UNAUTHORIZED("A0401", "未登录或登录已过期"),
    FORBIDDEN("A0403", "无权限访问"),
    NOT_FOUND("A0404", "资源不存在"),
    METHOD_NOT_ALLOWED("A0405", "请求方法不支持"),
    TOO_MANY_REQUESTS("A0429", "请求过于频繁"),
    BIZ_ERROR("B0001", "业务处理失败"),
    SYSTEM_ERROR("C0001", "系统繁忙，请稍后再试");

    private final String code;
    private final String message;

    GlobalErrorCode(String code, String message) {
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
