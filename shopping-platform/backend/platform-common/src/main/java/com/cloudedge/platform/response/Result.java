package com.cloudedge.platform.response;

import com.cloudedge.platform.exception.ErrorCode;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.LocalDateTime;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class Result<T> {
    private String code;
    private String message;
    private T data;
    private boolean success;
    private LocalDateTime timestamp;

    public Result() {
    }

    public Result(String code, String message, T data, boolean success, LocalDateTime timestamp) {
        this.code = code;
        this.message = message;
        this.data = data;
        this.success = success;
        this.timestamp = timestamp;
    }

    public static <T> Result<T> success() {
        return success(null);
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(
                GlobalErrorCode.SUCCESS.getCode(),
                GlobalErrorCode.SUCCESS.getMessage(),
                data,
                true,
                LocalDateTime.now()
        );
    }

    public static <T> Result<T> fail(String code, String message) {
        return new Result<>(
                code,
                message,
                null,
                false,
                LocalDateTime.now()
        );
    }

    public static <T> Result<T> fail(ErrorCode errorCode) {
        return fail(errorCode.getCode(), errorCode.getMessage());
    }

    public static <T> Result<T> fail(ErrorCode errorCode, String message) {
        return fail(errorCode.getCode(), message);
    }

    public String getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }

    public T getData() {
        return data;
    }

    public boolean isSuccess() {
        return success;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }
}
