package com.cloudedge.platform.user.enums;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum UserTypeEnum {

    C_END(1, "C端用户"),
    ADMIN(2, "后台管理员");

    private final Integer code;
    private final String desc;

}
