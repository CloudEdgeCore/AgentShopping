package com.cloudedge.platform.user.model.vo;

import lombok.Builder;
import lombok.Data;

@Builder
@Data
public class LoginResponse {

    private String accessToken;
    private String tokenType;
    private Long expiresIn;
    private UserInfoResponse userInfo;
}
