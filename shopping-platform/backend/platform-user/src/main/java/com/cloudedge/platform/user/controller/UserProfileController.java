package com.cloudedge.platform.user.controller;

import com.cloudedge.platform.response.Result;
import com.cloudedge.platform.user.model.dto.UpdateProfileRequest;
import com.cloudedge.platform.user.model.vo.UserInfoResponse;
import com.cloudedge.platform.user.service.impl.UserProfileServiceImpl;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/user/profile")
public class UserProfileController {
    @Autowired
    UserProfileServiceImpl userProfileService;

    @GetMapping
    public Result<UserInfoResponse> getCurrentProfile(){
        return Result.success(userProfileService.getCurrentProfile());
    }

    @PutMapping
    public Result<UserInfoResponse> updateCurrentProfile(@Valid @RequestBody UpdateProfileRequest request){
        return Result.success(userProfileService.updateCurrentProfile(request));
    }
}
