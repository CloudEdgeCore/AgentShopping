package com.cloudedge.platform.user.service.impl;

import com.cloudedge.platform.user.mapper.UserRbacMapper;
import com.cloudedge.platform.user.model.dto.UserRbacProfile;
import com.cloudedge.platform.user.service.UserRbacService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;

@Service
public class UserRbacServiceImpl implements UserRbacService {
    @Autowired
    private UserRbacMapper userRbacMapper;

    @Override
    public UserRbacProfile getUserRbacProfile(Long userId) {
        if (userId == null) return UserRbacProfile.builder().build();

        return UserRbacProfile.builder()
                .roles(distinct(userRbacMapper.selectRoleCodesByUserId(userId)))
                .permissions(distinct(userRbacMapper.selectPermissionCodesByUserId(userId)))
                .build();
    }

    private List<String> distinct(List<String> values){
        if (values == null || values.isEmpty()) return Collections.emptyList();

        LinkedHashSet<String> set = new LinkedHashSet<>();
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                set.add(value);
            }
        }
        return new ArrayList<>(set);
    }
}
