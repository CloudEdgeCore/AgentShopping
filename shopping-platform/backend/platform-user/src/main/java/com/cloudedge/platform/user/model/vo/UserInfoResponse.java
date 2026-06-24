package com.cloudedge.platform.user.model.vo;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Builder
@Data
public class UserInfoResponse {

    private Long userId;
    private String username;
    private String nickname;
    private Integer userType;
    private String mobile;
    private String email;
    private String avatarUrl;
    private Integer gender;
    private List<String> roles;
    private List<String> permissions;
}
