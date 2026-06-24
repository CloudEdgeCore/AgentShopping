package com.cloudedge.platform.user.service;

import com.cloudedge.platform.user.model.dto.UserRbacProfile;

public interface UserRbacService {

    UserRbacProfile getUserRbacProfile(Long userId);
}
