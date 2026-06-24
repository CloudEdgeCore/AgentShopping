package com.cloudedge.platform.handler;

import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.response.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BizException.class)
    public ResponseEntity<Result<Void>> handleBizException(BizException e, HttpServletRequest request) {
        log.warn("Business exception, uri={}, code={}, message={}",
                request.getRequestURI(), e.getCode(), e.getMessage());
        return ResponseEntity.status(resolveHttpStatus(e.getCode()))
                .body(Result.fail(e.getCode(), e.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Result<Void>> handleMethodArgumentNotValid(MethodArgumentNotValidException e,
                                                                     HttpServletRequest request) {
        String message = getBindingMessage(e.getBindingResult());
        log.warn("Validation exception, uri={}, message={}", request.getRequestURI(), message);
        return ResponseEntity.badRequest()
                .body(Result.fail(GlobalErrorCode.BAD_REQUEST, message));
    }

    @ExceptionHandler(BindException.class)
    public ResponseEntity<Result<Void>> handleBindException(BindException e, HttpServletRequest request) {
        String message = getBindingMessage(e.getBindingResult());
        log.warn("Bind exception, uri={}, message={}", request.getRequestURI(), message);
        return ResponseEntity.badRequest()
                .body(Result.fail(GlobalErrorCode.BAD_REQUEST, message));
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<Result<Void>> handleConstraintViolation(ConstraintViolationException e,
                                                                  HttpServletRequest request) {
        String message = e.getConstraintViolations().stream()
                .findFirst()
                .map(ConstraintViolation::getMessage)
                .orElse(GlobalErrorCode.BAD_REQUEST.getMessage());
        log.warn("Constraint violation, uri={}, message={}", request.getRequestURI(), message);

        return ResponseEntity.badRequest()
                .body(Result.fail(GlobalErrorCode.BAD_REQUEST, message));
    }

    @ExceptionHandler({
            MissingServletRequestParameterException.class,
            HttpMessageNotReadableException.class,
            MethodArgumentTypeMismatchException.class
    })
    public ResponseEntity<Result<Void>> handleBadRequestException(Exception e, HttpServletRequest request) {
        log.warn("Bad request exception, uri={}, message={}", request.getRequestURI(), e.getMessage());
        log.debug("Request validation exception", e);
        return ResponseEntity.badRequest()
                .body(Result.fail(GlobalErrorCode.BAD_REQUEST, GlobalErrorCode.BAD_REQUEST.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Result<Void>> handleException(Exception e, HttpServletRequest request) {
        log.error("Unhandled exception, uri={}", request.getRequestURI(), e);
        return ResponseEntity.internalServerError()
                .body(Result.fail(GlobalErrorCode.SYSTEM_ERROR));
    }

    private String getBindingMessage(BindingResult bindingResult) {
        FieldError fieldError = bindingResult.getFieldError();
        return fieldError == null ? GlobalErrorCode.BAD_REQUEST.getMessage() : fieldError.getDefaultMessage();
    }

    private HttpStatus resolveHttpStatus(String code) {
        if (GlobalErrorCode.UNAUTHORIZED.getCode().equals(code)) {
            return HttpStatus.UNAUTHORIZED;
        }
        if (GlobalErrorCode.FORBIDDEN.getCode().equals(code)) {
            return HttpStatus.FORBIDDEN;
        }
        if (GlobalErrorCode.NOT_FOUND.getCode().equals(code)) {
            return HttpStatus.NOT_FOUND;
        }
        if (GlobalErrorCode.METHOD_NOT_ALLOWED.getCode().equals(code)) {
            return HttpStatus.METHOD_NOT_ALLOWED;
        }
        if (GlobalErrorCode.TOO_MANY_REQUESTS.getCode().equals(code)) {
            return HttpStatus.TOO_MANY_REQUESTS;
        }
        if (GlobalErrorCode.SYSTEM_ERROR.getCode().equals(code)) {
            return HttpStatus.INTERNAL_SERVER_ERROR;
        }
        return HttpStatus.BAD_REQUEST;
    }
}
