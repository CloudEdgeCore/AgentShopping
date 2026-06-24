package com.cloudedge.platform.user.service;

import com.cloudedge.platform.user.model.dto.UpdateProfileRequest;
import com.cloudedge.platform.user.model.vo.UserInfoResponse;
import jakarta.validation.Valid;

public interface UserProfileService {
    UserInfoResponse getCurrentProfile();

    UserInfoResponse updateCurrentProfile(@Valid UpdateProfileRequest request);
}
