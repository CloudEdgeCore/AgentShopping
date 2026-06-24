package com.cloudedge.platform.inventory.support;

import com.cloudedge.platform.context.UserContext;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.exception.GlobalErrorCode;
import com.cloudedge.platform.model.LoginUser;
import org.springframework.stereotype.Component;

@Component
public class InventoryAdminSupport {
    private static final Integer ADMIN_USER_TYPE = 2;

    public void requireAdminUser(){
        LoginUser loginUser = UserContext.get();
        if(loginUser == null || loginUser.getUserId() == null) throw new BizException(GlobalErrorCode.UNAUTHORIZED);
        if (!ADMIN_USER_TYPE.equals(loginUser.getUserType())) throw new BizException(GlobalErrorCode.FORBIDDEN);
    }
}
