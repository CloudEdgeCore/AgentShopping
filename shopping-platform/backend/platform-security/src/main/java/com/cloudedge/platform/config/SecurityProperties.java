package com.cloudedge.platform.config;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.util.ArrayList;
import java.util.List;

@Data
@Validated
@ConfigurationProperties(prefix = "platform.security")
public class SecurityProperties {

    @NotBlank
    @Size(min = 32)
    private String secretKey = "cloudedge-shopping-platform-jwt-secret-2026";

    @Min(60)
    private long accessTokenValiditySeconds = 7200;

    private String tokenHeader = "Authorization";

    private String tokenPrefix = "Bearer ";

    private List<String> permitAllUrls = new ArrayList<>(List.of(
            "/auth/login",
            "/actuator/health",
            "/error",
            "/doc.html",
            "/swagger-ui/**",
            "/v3/api-docs/**"
    ));
}
