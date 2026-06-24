package com.cloudedge.platform.security;

import com.cloudedge.platform.model.LoginUser;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.List;

@Component("rbac")
public class RbacSecurityService {
    private static final Integer ADMIN_USER_TYPE = 2;
    private static final String SUPER_ADMIN_ROLE = "SUPER_ADMIN";
    private static final String ALL_PERMISSION = "*:*:*";

    public boolean hasRole(String roleCode){
        LoginUser loginUser = currentUser();
        if (!isBackOfficeUser(loginUser) || !hasText(roleCode)) return false;

        return isSuperAdmin(loginUser) || safeList(loginUser.getRoles()).contains(roleCode);
    }

    public boolean hasAnyRole(String... roleCodes) {
        return Arrays.stream(roleCodes).anyMatch(this::hasRole);
    }

    public boolean hasPermission(String permissionCode) {
        LoginUser loginUser = currentUser();
        if (!isBackOfficeUser(loginUser) || !hasText(permissionCode)) {
            return false;
        }
        return isSuperAdmin(loginUser) || safeList(loginUser.getPermissions()).contains(permissionCode);
    }

    public boolean hasAnyPermission(String... permissionCodes) {
        return Arrays.stream(permissionCodes).anyMatch(this::hasPermission);
    }

    private List<String> safeList(List<String> values) {
        return values == null ? Collections.emptyList() : values;
    }

    private boolean isSuperAdmin(LoginUser loginUser) {
        return safeList(loginUser.getRoles()).contains(SUPER_ADMIN_ROLE) || safeList(loginUser.getPermissions()).contains(ALL_PERMISSION);
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private boolean isBackOfficeUser(LoginUser loginUser) {
        return loginUser != null && ADMIN_USER_TYPE.equals(loginUser.getUserType());
    }

    private LoginUser currentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null) return null;

        if (!(authentication.getPrincipal() instanceof LoginUser loginUser)) return null;

        return loginUser;
    }
}
