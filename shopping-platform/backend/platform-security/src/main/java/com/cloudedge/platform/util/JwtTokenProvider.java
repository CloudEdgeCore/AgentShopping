package com.cloudedge.platform.util;

import com.cloudedge.platform.config.SecurityProperties;
import com.cloudedge.platform.exception.JwtAuthenticationException;
import com.cloudedge.platform.model.LoginUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Collections;
import java.util.Date;
import java.util.List;

@Component
@RequiredArgsConstructor
public class JwtTokenProvider {

    private static final String CLAIM_USERNAME = "username";
    private static final String CLAIM_USER_TYPE = "userType";
    private static final String CLAIM_ROLES = "roles";
    private static final String CLAIM_PERMISSIONS = "permissions";

    private final SecurityProperties securityProperties;

    public String createAccessToken(LoginUser loginUser) {
        Instant now = Instant.now();

        return Jwts.builder()
                .subject(String.valueOf(loginUser.getUserId()))
                .claim(CLAIM_USERNAME, loginUser.getUserName())
                .claim(CLAIM_USER_TYPE, loginUser.getUserType())
                .claim(CLAIM_PERMISSIONS, loginUser.getPermissions())
                .claim(CLAIM_ROLES, loginUser.getRoles())
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(securityProperties.getAccessTokenValiditySeconds())))
                .signWith(getSecretKey(), Jwts.SIG.HS256)
                .compact();
    }

    private SecretKey getSecretKey() {
        return Keys.hmacShaKeyFor(securityProperties.getSecretKey().getBytes(StandardCharsets.UTF_8));
    }

    public LoginUser parseAccessToken(String token) {
        try {
            Claims claims = parseClaims(token);
            return buildLoginUser(claims);
        } catch (JwtException | IllegalArgumentException e) {
            throw new JwtAuthenticationException("Token invalid or expired", e);
        }
    }

    public long getRemainingValiditySeconds(String token) {
        try {
            Claims claims = parseClaims(token);
            Date expiration = claims.getExpiration();
            if (expiration == null) {
                return 0;
            }
            long seconds = Duration.between(Instant.now(), expiration.toInstant()).getSeconds();
            return Math.max(seconds, 0);
        } catch (ExpiredJwtException ex) {
            return 0;
        } catch (JwtException | IllegalArgumentException ex) {
            throw new JwtAuthenticationException("Token invalid or expired", ex);
        }
    }

    private LoginUser buildLoginUser(Claims claims) {
        List<?> rawPermissions = claims.get(CLAIM_PERMISSIONS, List.class);
        List<String> permissions = rawPermissions == null ? Collections.emptyList() : rawPermissions.stream()
                .map(String::valueOf).toList();

        Number userTypeNumber = claims.get(CLAIM_USER_TYPE, Number.class);
        return LoginUser.builder()
                .userId(Long.valueOf(claims.getSubject()))
                .userName(claims.get(CLAIM_USERNAME, String.class))
                .userType(userTypeNumber == null ? null : userTypeNumber.intValue())
                .permissions(permissions)
                .build();
    }

    public String resolveToken(HttpServletRequest request) {
        String tokenValue = request.getHeader(securityProperties.getTokenHeader());
        if (tokenValue == null || tokenValue.isBlank()) {
            return null;
        }
        String tokenPrefix = securityProperties.getTokenPrefix();
        if (tokenPrefix != null && !tokenPrefix.isBlank() && tokenValue.startsWith(tokenPrefix)) {
            return tokenValue.substring(tokenPrefix.length());
        }
        return tokenValue;
    }

    private Claims parseClaims(String token) {
        return Jwts.parser()
                .verifyWith(getSecretKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
