package com.cloudedge.platform.logging;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestTraceFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RequestTraceFilter.class);

    private final PlatformLoggingProperties loggingProperties;

    public RequestTraceFilter(PlatformLoggingProperties loggingProperties) {
        this.loggingProperties = loggingProperties;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        if (!loggingProperties.getTrace().isEnabled() && !loggingProperties.getAccess().isEnabled()) {
            return true;
        }
        String requestUri = request.getRequestURI();
        return loggingProperties.getAccess().getExcludePaths().stream()
                .anyMatch(requestUri::startsWith);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        long startTime = System.currentTimeMillis();
        String traceId = resolveTraceId(request);
        String requestUri = buildRequestUri(request);
        String clientIp = resolveClientIp(request);
        Throwable failure = null;

        MDC.put(LoggingMdcConstants.TRACE_ID, traceId);
        MDC.put(LoggingMdcConstants.REQUEST_ID, traceId);
        MDC.put(LoggingMdcConstants.METHOD, request.getMethod());
        MDC.put(LoggingMdcConstants.URI, requestUri);
        MDC.put(LoggingMdcConstants.CLIENT_IP, clientIp);

        if (loggingProperties.getTrace().isResponseHeaderEnabled()) {
            response.setHeader(loggingProperties.getTrace().getRequestHeader(), traceId);
        }

        try {
            filterChain.doFilter(request, response);
        } catch (IOException | ServletException | RuntimeException ex) {
            failure = ex;
            throw ex;
        } finally {
            if (loggingProperties.getAccess().isEnabled()) {
                long durationMs = System.currentTimeMillis() - startTime;
                logAccess(request, response, requestUri, clientIp, durationMs, failure);
            }
            MDC.clear();
        }
    }

    private void logAccess(HttpServletRequest request,
                           HttpServletResponse response,
                           String requestUri,
                           String clientIp,
                           long durationMs,
                           Throwable failure) {
        int status = response.getStatus();
        MDC.put(LoggingMdcConstants.STATUS, String.valueOf(status));
        MDC.put(LoggingMdcConstants.DURATION_MS, String.valueOf(durationMs));
        String message = "HTTP request completed method={}, uri={}, status={}, durationMs={}, clientIp={}";
        if (failure != null || status >= 500) {
            log.error(message, request.getMethod(), requestUri, status, durationMs, clientIp);
            return;
        }
        if (durationMs >= loggingProperties.getAccess().getSlowThresholdMs()) {
            log.warn(message, request.getMethod(), requestUri, status, durationMs, clientIp);
            return;
        }
        log.info(message, request.getMethod(), requestUri, status, durationMs, clientIp);
    }

    private String resolveTraceId(HttpServletRequest request) {
        String headerName = loggingProperties.getTrace().getRequestHeader();
        String candidate = headerName == null ? null : request.getHeader(headerName);
        if (StringUtils.hasText(candidate)) {
            String sanitized = candidate.trim();
            if (sanitized.length() <= 64) {
                return sanitized;
            }
        }
        return UUID.randomUUID().toString().replace("-", "");
    }

    private String buildRequestUri(HttpServletRequest request) {
        String query = request.getQueryString();
        if (!StringUtils.hasText(query)) {
            return request.getRequestURI();
        }
        return request.getRequestURI() + "?" + query;
    }

    private String resolveClientIp(HttpServletRequest request) {
        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (StringUtils.hasText(forwardedFor)) {
            return forwardedFor.split(",")[0].trim();
        }
        String realIp = request.getHeader("X-Real-IP");
        if (StringUtils.hasText(realIp)) {
            return realIp.trim();
        }
        return request.getRemoteAddr();
    }
}
