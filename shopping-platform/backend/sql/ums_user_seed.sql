USE shopping;

DELETE FROM ums_user_role
WHERE user_id = 1000000004;

DELETE FROM ums_role_permission
WHERE role_id = 2000000001;

DELETE FROM ums_permission
WHERE id BETWEEN 3000000001 AND 3000000033
   OR id BETWEEN 3000000041 AND 3000000043
   OR id BETWEEN 3000000051 AND 3000000056
   OR id BETWEEN 3000000061 AND 3000000065
   OR id BETWEEN 3000000071 AND 3000000072
   OR id = 3000000099;

DELETE FROM ums_role
WHERE id = 2000000001;

DELETE FROM ums_user
WHERE username IN ('zhangsan', 'lisi', 'wangwu', 'admin', 'disabled_user');

INSERT INTO ums_user (
    id,
    username,
    password,
    nickname,
    mobile,
    email,
    avatar_url,
    gender,
    user_type,
    status,
    last_login_time,
    last_login_ip,
    deleted
) VALUES
(
    1000000001,
    'zhangsan',
    '$2a$10$t.bPJp8CDgOjmVPtbPw9v.fZdQv11ka5pakMTOOooLVqEtFMquMkG',
    'zhangsan',
    '13800000001',
    'zhangsan@test.com',
    NULL,
    1,
    1,
    1,
    NULL,
    NULL,
    0
),
(
    1000000002,
    'lisi',
    '$2a$10$kqzrUiUUZYopbgnhG.4pz.fT2bu.2LBOlrZEwAalZrSoI6fe2qHKW',
    'lisi',
    '13800000002',
    'lisi@test.com',
    NULL,
    2,
    1,
    1,
    NULL,
    NULL,
    0
),
(
    1000000003,
    'wangwu',
    '$2a$10$JfnNIpFED76w5Zfu4Zh0h.1apyUdBobh5nB5uGaRxP9oQG2sGPAxW',
    'wangwu',
    '13800000003',
    'wangwu@test.com',
    NULL,
    1,
    1,
    1,
    NULL,
    NULL,
    0
),
(
    1000000004,
    'admin',
    '$2a$10$SFAVgppGBx6o83PdXbdeEexDPMIoWBPAcAbs/2MGtmkQVNMhLwyE.',
    'platform_admin',
    '13800000004',
    'admin@test.com',
    NULL,
    1,
    2,
    1,
    NULL,
    NULL,
    0
),
(
    1000000005,
    'disabled_user',
    '$2a$10$Wd8JF4j/cky0qkgLxPQqMeGZjnB5ZrNKOMX6NXxr0ycV.mK7gPYaK',
    'disabled_user',
    '13800000005',
    'disabled_user@test.com',
    NULL,
    0,
    1,
    0,
    NULL,
    NULL,
    0
);

INSERT INTO ums_role (
    id,
    role_code,
    role_name,
    sort,
    status,
    remark,
    deleted
) VALUES
(
    2000000001,
    'SUPER_ADMIN',
    'Super Admin',
    0,
    1,
    'all back-office permissions',
    0
);

INSERT INTO ums_permission (
    id,
    permission_code,
    permission_name,
    module,
    sort,
    status,
    remark,
    deleted
) VALUES
(3000000001, 'pms:brand:list', 'Brand List', 'product', 1, 1, NULL, 0),
(3000000002, 'pms:brand:create', 'Create Brand', 'product', 2, 1, NULL, 0),
(3000000003, 'pms:brand:update', 'Update Brand', 'product', 3, 1, NULL, 0),
(3000000004, 'pms:brand:delete', 'Delete Brand', 'product', 4, 1, NULL, 0),

(3000000011, 'pms:category:list', 'Category List', 'product', 11, 1, NULL, 0),
(3000000012, 'pms:category:create', 'Create Category', 'product', 12, 1, NULL, 0),
(3000000013, 'pms:category:update', 'Update Category', 'product', 13, 1, NULL, 0),
(3000000014, 'pms:category:delete', 'Delete Category', 'product', 14, 1, NULL, 0),

(3000000021, 'pms:product:list', 'Product List', 'product', 21, 1, NULL, 0),
(3000000022, 'pms:product:detail', 'Product Detail', 'product', 22, 1, NULL, 0),
(3000000023, 'pms:product:create', 'Create Product', 'product', 23, 1, NULL, 0),
(3000000024, 'pms:product:update', 'Update Product', 'product', 24, 1, NULL, 0),
(3000000025, 'pms:product:publish', 'Publish Product', 'product', 25, 1, NULL, 0),
(3000000026, 'pms:product:delete', 'Delete Product', 'product', 26, 1, NULL, 0),

(3000000031, 'wms:stock:list', 'Stock List', 'inventory', 31, 1, NULL, 0),
(3000000032, 'wms:stock:create', 'Create Stock', 'inventory', 32, 1, NULL, 0),
(3000000033, 'wms:stock:update', 'Update Stock', 'inventory', 33, 1, NULL, 0),

(3000000041, 'oms:order:list', 'Order List', 'order', 41, 1, NULL, 0),
(3000000042, 'oms:order:detail', 'Order Detail', 'order', 42, 1, NULL, 0),
(3000000043, 'oms:order:cancel', 'Cancel Order', 'order', 43, 1, NULL, 0),

(3000000051, 'sms:coupon:list', 'Coupon List', 'marketing', 51, 1, NULL, 0),
(3000000052, 'sms:coupon:detail', 'Coupon Detail', 'marketing', 52, 1, NULL, 0),
(3000000053, 'sms:coupon:create', 'Create Coupon', 'marketing', 53, 1, NULL, 0),
(3000000054, 'sms:coupon:update', 'Update Coupon', 'marketing', 54, 1, NULL, 0),
(3000000055, 'sms:coupon:enable', 'Enable Coupon', 'marketing', 55, 1, NULL, 0),
(3000000056, 'sms:coupon:disable', 'Disable Coupon', 'marketing', 56, 1, NULL, 0),

(3000000061, 'sms:flashsale:list', 'Flash Sale List', 'marketing', 61, 1, NULL, 0),
(3000000062, 'sms:flashsale:detail', 'Flash Sale Detail', 'marketing', 62, 1, NULL, 0),
(3000000063, 'sms:flashsale:create', 'Create Flash Sale', 'marketing', 63, 1, NULL, 0),
(3000000064, 'sms:flashsale:update', 'Update Flash Sale', 'marketing', 64, 1, NULL, 0),
(3000000065, 'sms:flashsale:delete', 'Delete Flash Sale', 'marketing', 65, 1, NULL, 0),

(3000000071, 'search:product:rebuild', 'Rebuild Product Index', 'search', 71, 1, NULL, 0),
(3000000072, 'search:product:sync', 'Sync Product Index', 'search', 72, 1, NULL, 0),

(3000000099, '*:*:*', 'Super Admin Wildcard', 'system', 99, 1, 'super admin wildcard', 0);

INSERT INTO ums_user_role (
    id,
    user_id,
    role_id,
    deleted
) VALUES
(
    2100000001,
    1000000004,
    2000000001,
    0
);

INSERT INTO ums_role_permission (
    id,
    role_id,
    permission_id,
    deleted
) VALUES
(2200000001, 2000000001, 3000000001, 0),
(2200000002, 2000000001, 3000000002, 0),
(2200000003, 2000000001, 3000000003, 0),
(2200000004, 2000000001, 3000000004, 0),
(2200000005, 2000000001, 3000000011, 0),
(2200000006, 2000000001, 3000000012, 0),
(2200000007, 2000000001, 3000000013, 0),
(2200000008, 2000000001, 3000000014, 0),
(2200000009, 2000000001, 3000000021, 0),
(2200000010, 2000000001, 3000000022, 0),
(2200000011, 2000000001, 3000000023, 0),
(2200000012, 2000000001, 3000000024, 0),
(2200000013, 2000000001, 3000000025, 0),
(2200000014, 2000000001, 3000000026, 0),
(2200000015, 2000000001, 3000000031, 0),
(2200000016, 2000000001, 3000000032, 0),
(2200000017, 2000000001, 3000000033, 0),
(2200000018, 2000000001, 3000000041, 0),
(2200000019, 2000000001, 3000000042, 0),
(2200000020, 2000000001, 3000000043, 0),
(2200000021, 2000000001, 3000000051, 0),
(2200000022, 2000000001, 3000000052, 0),
(2200000023, 2000000001, 3000000053, 0),
(2200000024, 2000000001, 3000000054, 0),
(2200000025, 2000000001, 3000000055, 0),
(2200000026, 2000000001, 3000000056, 0),
(2200000027, 2000000001, 3000000061, 0),
(2200000028, 2000000001, 3000000062, 0),
(2200000029, 2000000001, 3000000063, 0),
(2200000030, 2000000001, 3000000064, 0),
(2200000031, 2000000001, 3000000065, 0),
(2200000032, 2000000001, 3000000071, 0),
(2200000033, 2000000001, 3000000072, 0),
(2200000034, 2000000001, 3000000099, 0);
