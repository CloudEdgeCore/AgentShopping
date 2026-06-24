package com.cloudedge.platform.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Builder;
import lombok.Data;
import lombok.Getter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

import java.io.Serializable;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.stream.Stream;

@Builder
@Data
@Getter
public class LoginUser implements Serializable {

    private Long userId;
    private String userName;
    private Integer userType;

    @Builder.Default
    private List<String> roles = Collections.emptyList();

    @Builder.Default
    private List<String> permissions = Collections.emptyList();

    @JsonIgnore
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return Stream.concat(
                        safeList(roles).stream()
                                .filter(this::hasText)
                                .map(role -> new SimpleGrantedAuthority("ROLE_" + role)),
                        safeList(permissions).stream()
                                .filter(this::hasText)
                                .map(SimpleGrantedAuthority::new)
                ).distinct()
                .toList();
    }

    private boolean hasText(String value) {
        return value != null && !value.isEmpty();
    }

    private List<String> safeList(List<String> values) {
        return values == null ? Collections.emptyList() : values;
    }
}
