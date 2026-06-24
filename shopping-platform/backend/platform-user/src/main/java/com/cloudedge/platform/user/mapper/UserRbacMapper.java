package com.cloudedge.platform.user.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface UserRbacMapper {

    @Select("""
            select distinct r.role_code
            from ums_user_role ur
            inner join ums_role r
                on r.id = ur.role_id
               and r.deleted = 0
               and r.status = 1
            where ur.user_id = #{userId}
              and ur.deleted = 0
            order by r.sort asc, r.id asc
            """)
    List<String> selectRoleCodesByUserId(Long userId);

    @Select("""
            select distinct p.permission_code
            from ums_user_role ur
            inner join ums_role r
                on r.id = ur.role_id
               and r.deleted = 0
               and r.status = 1
            inner join ums_role_permission rp
                on rp.role_id = r.id
               and rp.deleted = 0
            inner join ums_permission p
                on p.id = rp.permission_id
               and p.deleted = 0
               and p.status = 1
            where ur.user_id = #{userId}
              and ur.deleted = 0
            order by p.sort asc, p.id asc
            """)
    List<String> selectPermissionCodesByUserId(Long userId);
}
