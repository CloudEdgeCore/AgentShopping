package com.cloudedge.platform.filter;

import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.exception.JwtAuthenticationException;
import com.cloudedge.platform.handler.RestAuthenticationEntryPoint;
import com.cloudedge.platform.logging.LoggingMdcConstants;
import com.cloudedge.platform.model.LoginUser;
import com.cloudedge.platform.util.JwtTokenProvider;
import com.cloudedge.platform.util.TokenBlacklistService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.slf4j.MDC;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider jwtTokenProvider;
    private final TokenBlacklistService tokenBlacklistService;
    private final RestAuthenticationEntryPoint restAuthenticationEntryPoint;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain) throws ServletException, IOException {
        try {
            String token = jwtTokenProvider.resolveToken(request);
            if (token != null && !token.isBlank() && SecurityContextHolder.getContext().getAuthentication() == null) {
                if (tokenBlacklistService.isBlacklisted(token)) {
                    throw new JwtAuthenticationException("Token has been revoked");
                }
                LoginUser loginUser = jwtTokenProvider.parseAccessToken(token);
                UserContext.set(loginUser);
                putLoginUserToMdc(loginUser);

                UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(loginUser, null, loginUser.getAuthorities());
                authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

                SecurityContextHolder.getContext().setAuthentication(authentication);
            }
            filterChain.doFilter(request, response);
        } catch (JwtAuthenticationException e) {
            SecurityContextHolder.clearContext();
            UserContext.clear();
            restAuthenticationEntryPoint.commence(request, response, new BadCredentialsException(e.getMessage(), e));
        } finally {
            UserContext.clear();
            MDC.remove(LoggingMdcConstants.USER_ID);
            MDC.remove(LoggingMdcConstants.USER_TYPE);
            MDC.remove(LoggingMdcConstants.USERNAME);
        }
    }

    private void putLoginUserToMdc(LoginUser loginUser) {
        if (loginUser == null) {
            return;
        }
        if (loginUser.getUserId() != null) {
            MDC.put(LoggingMdcConstants.USER_ID, String.valueOf(loginUser.getUserId()));
        }
        if (loginUser.getUserType() != null) {
            MDC.put(LoggingMdcConstants.USER_TYPE, String.valueOf(loginUser.getUserType()));
        }
        if (loginUser.getUserName() != null && !loginUser.getUserName().isBlank()) {
            MDC.put(LoggingMdcConstants.USERNAME, loginUser.getUserName());
        }
    }
}
