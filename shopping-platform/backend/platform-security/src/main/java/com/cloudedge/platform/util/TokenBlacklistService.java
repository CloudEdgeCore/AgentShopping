package com.cloudedge.platform.util;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;

@Component
public class TokenBlacklistService {

    private static final String KEY_PREFIX = "security:jwt:blacklist:";

    private final StringRedisTemplate stringRedisTemplate;

    public TokenBlacklistService(StringRedisTemplate stringRedisTemplate) {
        this.stringRedisTemplate = stringRedisTemplate;
    }

    public void blacklist(String token, long ttlSeconds) {
        if (token == null || token.isBlank() || ttlSeconds <= 0) {
            return;
        }
        try {
            stringRedisTemplate.opsForValue().set(buildKey(token), "1", Duration.ofSeconds(ttlSeconds));
        } catch (RuntimeException ignored) {
            // Redis is an optimization for token revocation. Ignore transient failures.
        }
    }

    public boolean isBlacklisted(String token) {
        if (token == null || token.isBlank()) {
            return false;
        }
        try {
            Boolean exists = stringRedisTemplate.hasKey(buildKey(token));
            return Boolean.TRUE.equals(exists);
        } catch (RuntimeException ignored) {
            // If Redis is temporarily unavailable, fall back to not-blacklisted.
            return false;
        }
    }

    private String buildKey(String token) {
        return KEY_PREFIX + sha256(token);
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 algorithm not available", ex);
        }
    }
}
