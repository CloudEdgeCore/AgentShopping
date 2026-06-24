package com.cloudedge.platform.marketing.support;

import com.cloudedge.platform.marketing.entity.CouponTemplateDO;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

@Component
public class CouponClaimRedisSupport {

    private static final DefaultRedisScript<Long> CLAIM_SCRIPT = new DefaultRedisScript<>();

    static {
        CLAIM_SCRIPT.setResultType(Long.class);
        CLAIM_SCRIPT.setScriptText("""
                local remainKey = KEYS[1]
                local userKey = KEYS[2]
                local defaultRemain = tonumber(ARGV[1])
                local defaultUserCount = tonumber(ARGV[2])
                local userLimit = tonumber(ARGV[3])
                if redis.call('EXISTS', remainKey) == 0 then
                    redis.call('SET', remainKey, defaultRemain)
                end
                if redis.call('EXISTS', userKey) == 0 then
                    redis.call('SET', userKey, defaultUserCount)
                end
                local remain = tonumber(redis.call('GET', remainKey) or '0')
                local userCount = tonumber(redis.call('GET', userKey) or '0')
                if remain <= 0 then
                    return 0
                end
                if userCount >= userLimit then
                    return 1
                end
                redis.call('DECR', remainKey)
                redis.call('INCR', userKey)
                return 2
                """);
    }

    private final ObjectProvider<StringRedisTemplate> redisTemplateProvider;

    public CouponClaimRedisSupport(ObjectProvider<StringRedisTemplate> redisTemplateProvider) {
        this.redisTemplateProvider = redisTemplateProvider;
    }

    public CouponClaimReserveResult tryReserve(CouponTemplateDO template, Long userId, long dbUserCount) {
        StringRedisTemplate redisTemplate = redisTemplateProvider.getIfAvailable();
        if (redisTemplate == null) {
            return CouponClaimReserveResult.SKIPPED;
        }

        long remain = Math.max(0, (long) template.getTotalCount() - template.getClaimedCount());
        try {
            Long result = redisTemplate.execute(
                    CLAIM_SCRIPT,
                    List.of(remainingKey(template.getId()), userCountKey(template.getId(), userId)),
                    String.valueOf(remain),
                    String.valueOf(dbUserCount),
                    String.valueOf(template.getPerUserLimit())
            );
            expireKeys(redisTemplate, template, userId);
            if (result == null) {
                return CouponClaimReserveResult.SKIPPED;
            }
            if (result == 0L) {
                return CouponClaimReserveResult.OUT_OF_STOCK;
            }
            if (result == 1L) {
                return CouponClaimReserveResult.USER_LIMIT_REACHED;
            }
            return CouponClaimReserveResult.RESERVED;
        } catch (RuntimeException ex) {
            return CouponClaimReserveResult.SKIPPED;
        }
    }

    public void rollbackReserve(Long templateId, Long userId) {
        StringRedisTemplate redisTemplate = redisTemplateProvider.getIfAvailable();
        if (redisTemplate == null) {
            return;
        }
        try {
            redisTemplate.opsForValue().increment(remainingKey(templateId));
            redisTemplate.opsForValue().decrement(userCountKey(templateId, userId));
        } catch (RuntimeException ignored) {
        }
    }

    private void expireKeys(StringRedisTemplate redisTemplate, CouponTemplateDO template, Long userId) {
        if (template.getReceiveEndTime() == null) {
            return;
        }
        Duration ttl = Duration.between(LocalDateTime.now(), template.getReceiveEndTime());
        if (ttl.isNegative() || ttl.isZero()) {
            return;
        }
        redisTemplate.expire(remainingKey(template.getId()), ttl);
        redisTemplate.expire(userCountKey(template.getId(), userId), ttl);
    }

    private String remainingKey(Long templateId) {
        return "coupon:template:remain:" + templateId;
    }

    private String userCountKey(Long templateId, Long userId) {
        return "coupon:template:user:" + templateId + ":" + userId;
    }
}
