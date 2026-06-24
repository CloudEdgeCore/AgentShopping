create table if not exists ums_user
(
    id              bigint unsigned not null comment 'userId',
    username        varchar(64)     not null comment 'username',
    password        varchar(100)    not null comment 'BCrypt password',
    nickname        varchar(64)     not null comment 'nickname',
    mobile          varchar(20)              default null comment 'phoneId',
    email           varchar(128)             default null comment 'email',
    avatar_url      varchar(255)             default null comment 'head image url',
    gender          tinyint         not null default 0 comment '0 not know 1 boy 2 girl',
    user_type       tinyint         not null default 1 comment '0-shopper 1-C-user 2-admin',
    status          tinyint         not null default 1 comment '0-disable 1-enable',
    last_login_time datetime                 default null comment 'last login time',
    last_login_ip   varchar(64)              default null comment 'last login ip',
    deleted         tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time     datetime        not null default current_timestamp comment 'create time',
    update_time     datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_username (username),
    unique key uk_mobile (mobile),
    unique key uk_email (email),
    key idx_user_type_status (user_type, status)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'user table';

create table if not exists ums_role(
    id bigint unsigned not null comment 'role id',
    role_code varchar(64) not null comment 'role code',
    role_name varchar(64) not null comment 'role name',
    sort int not null default 0 comment 'sort',
    status tinyint not null default 1 comment '0-disabled 1-enabled',
    remark varchar(255) not null default null comment 'remark',
    deleted tinyint not null default 0 comment 'logic delete 0-false 1-true',
    create_time datetime not null default current_timestamp comment 'create time',
    update_time datetime not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_role_code(role_code),
    key idx_role_status(status)
) engine = InnoDB default charset = utf8mb4 collate = utf8mb4_unicode_ci comment 'rbac role';

create table if not exists ums_permission(
    id bigint unsigned not null comment 'permission id',
    permission_code varchar(100) not null comment 'permission code',
    permission_name varchar(64) not null comment 'permission name',
    module varchar(64) default null comment 'module name',
    sort             int             not null default 0 comment 'sort',
    status           tinyint         not null default 1 comment '0-disabled 1-enabled',
    remark           varchar(255)             default null comment 'remark',
    deleted          tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time      datetime        not null default current_timestamp comment 'create time',
    update_time      datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_permission_code (permission_code),
    key idx_permission_status (status)
) engine = InnoDB default charset = utf8mb4 collate = utf8mb4_unicode_ci comment 'rbac permission';

create table if not exists ums_user_role(
    id bigint unsigned not null comment 'id',
    user_id bigint unsigned not null comment 'user id',
    role_id bigint unsigned not null comment 'role id',
    deleted     tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time datetime        not null default current_timestamp comment 'create time',
    update_time datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_user_role (user_id, role_id),
    key idx_role_id (role_id)
)engine = InnoDB default charset = utf8mb4 collate = utf8mb4_unicode_ci comment 'user role relation';

create table if not exists ums_role_permission
(
    id            bigint unsigned not null comment 'id',
    role_id       bigint unsigned not null comment 'role id',
    permission_id bigint unsigned not null comment 'permission id',
    deleted       tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time   datetime        not null default current_timestamp comment 'create time',
    update_time   datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_role_permission (role_id, permission_id),
    key idx_permission_id (permission_id)
) engine = InnoDB default charset = utf8mb4 collate = utf8mb4_unicode_ci comment 'role permission relation';

create table if not exists ums_user_address
(
    id              bigint unsigned not null comment 'addressId',
    user_id         bigint unsigned not null comment 'userId',
    receiver_name   varchar(64)     not null comment 'receiverName',
    receiver_mobile varchar(20)     not null comment 'receiverMobile',
    province_name   varchar(32)              default null comment 'provinceName',
    province_code   varchar(32)              default null comment 'provinceCode',
    city_name       varchar(32)              default null comment 'cityName',
    city_code       varchar(32)              default null comment 'cityCode',
    district_name   varchar(32)              default null comment 'districtName',
    district_code   varchar(32)              default null comment 'districtCode',
    detail_address  varchar(255)    not null comment 'detailAddress',
    postal_code     varchar(16)              default null comment 'zip code',
    is_default      tinyint         not null default 0 comment '0-false 1-true',
    status          tinyint         not null default 1 comment '0-disable 1-enable',
    deleted         tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time     datetime        not null default current_timestamp comment 'create time',
    update_time     datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    key idx_user_id (user_id),
    key idx_user_default (user_id, is_default)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'user receiver address';

create table if not exists cart_item
(
    id           bigint unsigned not null comment 'cart item id',
    user_id      bigint unsigned not null comment 'user id',
    sku_id       bigint unsigned not null comment 'sku id',
    spu_id       bigint unsigned not null comment 'spu id',
    spu_name     varchar(128)    not null comment 'spu name snapshot',
    sku_name     varchar(128)    not null comment 'sku name snapshot',
    sku_image    varchar(255)             default null comment 'sku image snapshot',
    sku_attr_text varchar(255)            default null comment 'sku attr snapshot',
    sale_price   decimal(10, 2)  not null default 0.00 comment 'sale price snapshot',
    quantity     int             not null default 1 comment 'quantity',
    checked      tinyint         not null default 1 comment '0-unchecked 1-checked',
    create_time  datetime        not null default current_timestamp comment 'create time',
    update_time  datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_user_sku (user_id, sku_id),
    key idx_user_checked (user_id, checked),
    key idx_user_update_time (user_id, update_time)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'shopping cart item table';


create table pms_category
(
    id          bigint unsigned not null comment 'categoryId',
    parent_id   bigint unsigned not null default 0 comment 'parentId',
    name        varchar(64)     not null comment 'category name',
    icon_url    varchar(255)             default null comment 'category icon',
    sort        int             not null default 0 comment 'sort',
    status      tinyint         not null default 1 comment '0-disable 1-enabled',
    deleted     tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time datetime        not null default current_timestamp comment 'create time',
    update_time datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_parent_name (parent_id, name),
    key idx_parent_status (parent_id, status)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'product category';


create table pms_brand
(
    id          bigint unsigned not null comment 'brandId',
    name        varchar(64)     not null comment 'brand name',
    logo_url    varchar(255)             default null comment 'brand logo',
    description varchar(500)             default null comment 'brand description',
    sort        int             not null default 0 comment 'sort',
    status      tinyint         not null default 1 comment '0-disabled 1-enabled',
    deleted     tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time datetime        not null default current_timestamp comment 'create time',
    update_time datetime        not null default current_timestamp on update current_timestamp comment 'update_time',
    primary key (id),
    unique uk_brand_name (name),
    key idx_brand_status (status)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'product category';

create table pms_spu
(
    id             bigint unsigned not null comment 'spuId',
    category_id    bigint unsigned not null comment 'categoryId',
    brand_id       bigint unsigned not null comment 'brandId',
    spu_name       varchar(128)    not null comment 'spu name',
    subtitle       varchar(255)             default null comment 'subtitle',
    cover_image    varchar(255)             default null comment 'cover image',
    album_images   text                     default null comment 'album images separated by comma',
    detail         text                     default null comment 'detail',
    publish_status tinyint         not null default 0 comment '0-unpublished 1-published',
    sort           int             not null default 0 comment 'sort',
    deleted        tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time    datetime        not null default current_timestamp comment 'create time',
    update_time    datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    key idx_category_publish (category_id, publish_status),
    key idx_brand_publish (brand_id, publish_status),
    key idx_publish_sort (publish_status, sort)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'product category';

create table pms_sku
(
    id           bigint unsigned not null comment 'skuId',
    spu_id       bigint unsigned not null comment 'spuId',
    sku_code     varchar(64)     not null comment 'sku code',
    sku_name     varchar(128)    not null comment 'sku name',
    image_url    varchar(255)             default null comment 'sku image',
    sale_price   decimal(10, 2)  not null default 0.00 comment 'sale price',
    market_price decimal(10, 2)  not null default 0.00 comment 'market price',
    attr_text    varchar(255)             default null comment 'sku attributes',
    is_default   tinyint         not null default 0 comment '0-false 1-true',
    status       tinyint         not null default 1 comment '0-disabled 1-enabled',
    deleted      tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time  datetime        not null default current_timestamp comment 'create time',
    update_time  datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    key idx_spu_status (spu_id, status),
    key idx_sku_code (sku_code)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'product sku';

create table wms_sku_stock(
    id bigint unsigned not null comment 'id',
    sku_id bigint unsigned not null comment 'skuId',
    total_stock int not null default 0 comment 'total stock',
    available_stock int not null default 0 comment 'available stock',
    locked_stock int not null default 0 comment 'locked stock',
    status tinyint not null default 1 comment '0-disabled 1-enabled',
    deleted tinyint not null default 0 comment 'logic delete 0-false 1-true',
    create_time datetime not null default current_timestamp comment 'create time',
    update_time datetime not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_sku_id(sku_id),
    key idx_status (status)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'sku stock';

create table wms_stock_lock_record(
    id bigint unsigned not null comment 'id',
    order_no varchar(64) not null comment 'order no',
    biz_type varchar(32) not null comment 'business type',
    sku_id bigint unsigned not null comment 'skuId',
    lock_quantity int not null comment 'lock quantity',
    status tinyint not null comment '1-locked 2-deducted 3-released',
    deleted tinyint not null default 0 comment 'logic delete 0-false 1-true',
    create_time datetime not null default current_timestamp comment 'create time',
    update_time datetime not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_order_biz_sku(order_no, biz_type, sku_id),
    key idx_order_biz_status(order_no, biz_type, status),
    key idx_sku_id(sku_id)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'stock lock record';

create table oms_order
(
    id              bigint unsigned not null comment 'id',
    order_no        varchar(64)     not null comment 'order no',
    user_id         bigint unsigned not null comment 'user id',
    address_id      bigint unsigned not null comment 'address id',
    status          tinyint         not null comment '10-pending_payment 20-paid 30-cancelled',
    total_quantity  int             not null default 0 comment 'total quantity',
    total_amount    decimal(10, 2)  not null default 0.00 comment 'original total amount',
    promotion_amount decimal(10, 2) not null default 0.00 comment 'promotion discount amount',
    coupon_amount   decimal(10, 2)  not null default 0.00 comment 'coupon discount amount',
    payable_amount  decimal(10, 2)  not null default 0.00 comment 'payable amount',
    coupon_user_id  bigint unsigned          default null comment 'locked coupon id',
    coupon_name     varchar(64)              default null comment 'coupon name snapshot',
    receiver_name   varchar(64)     not null comment 'receiver name snapshot',
    receiver_mobile varchar(20)     not null comment 'receiver mobile snapshot',
    province_name   varchar(32)              default null comment 'province name snapshot',
    city_name       varchar(32)              default null comment 'city name snapshot',
    district_name   varchar(32)              default null comment 'district name snapshot',
    detail_address  varchar(255)    not null comment 'detail address snapshot',
    postal_code     varchar(16)              default null comment 'postal code snapshot',
    remark          varchar(500)             default null comment 'user remark',
    cancel_reason   varchar(255)             default null comment 'cancel reason',
    pay_time        datetime                 default null comment 'pay time',
    cancel_time     datetime                 default null comment 'cancel time',
    deleted         tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time     datetime        not null default current_timestamp comment 'create time',
    update_time     datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_order_no (order_no),
    key idx_user_status (user_id, status),
    key idx_user_create_time (user_id, create_time)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'order main table';

create table oms_order_item
(
    id            bigint unsigned not null comment 'id',
    order_id      bigint unsigned not null comment 'order id',
    order_no      varchar(64)     not null comment 'order no',
    sku_id        bigint unsigned not null comment 'sku id',
    spu_id        bigint unsigned not null comment 'spu id',
    spu_name      varchar(128)    not null comment 'spu name snapshot',
    sku_name      varchar(128)    not null comment 'sku name snapshot',
    sku_image     varchar(255)             default null comment 'sku image snapshot',
    sku_attr_text varchar(255)             default null comment 'sku attr snapshot',
    original_price decimal(10, 2) not null default 0.00 comment 'original price snapshot',
    sale_price    decimal(10, 2)  not null default 0.00 comment 'final sale price snapshot',
    quantity      int             not null default 1 comment 'quantity',
    promotion_amount decimal(10, 2) not null default 0.00 comment 'line promotion amount',
    total_amount  decimal(10, 2)  not null default 0.00 comment 'line amount',
    deleted       tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time   datetime        not null default current_timestamp comment 'create time',
    update_time   datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    key idx_order_no (order_no),
    key idx_order_id (order_id)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'order item table';

create table pay_transaction
(
    id           bigint unsigned not null comment 'id',
    payment_no   varchar(64)     not null comment 'payment no',
    order_no     varchar(64)     not null comment 'order no',
    user_id      bigint unsigned not null comment 'user id',
    pay_channel  tinyint         not null comment '10-mock',
    pay_status   tinyint         not null comment '10-unpaid 20-success 30-closed',
    amount       decimal(10, 2)  not null default 0.00 comment 'payment amount',
    subject      varchar(128)    not null comment 'payment subject',
    success_time datetime                 default null comment 'success time',
    close_time   datetime                 default null comment 'close time',
    close_reason varchar(255)             default null comment 'close reason',
    deleted      tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time  datetime        not null default current_timestamp comment 'create time',
    update_time  datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_payment_no (payment_no),
    unique key uk_order_no (order_no),
    key idx_user_status (user_id, pay_status)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'payment transaction table';

create table sms_coupon_template
(
    id                 bigint unsigned not null comment 'template id',
    name               varchar(64)     not null comment 'coupon name',
    coupon_type        tinyint         not null comment '10-full reduction 20-discount',
    threshold_amount   decimal(10, 2)  not null default 0.00 comment 'threshold amount',
    discount_amount    decimal(10, 2)  not null default 0.00 comment 'discount amount',
    discount_rate      decimal(4, 2)            default null comment 'discount rate',
    total_count        int             not null default 0 comment 'total count',
    claimed_count      int             not null default 0 comment 'claimed count',
    per_user_limit     int             not null default 1 comment 'per user limit',
    scope_type         tinyint         not null comment '10-all 20-category 30-spu 40-sku',
    receive_start_time datetime        not null comment 'receive start time',
    receive_end_time   datetime        not null comment 'receive end time',
    valid_from         datetime        not null comment 'coupon valid from',
    valid_to           datetime        not null comment 'coupon valid to',
    description        varchar(500)             default null comment 'description',
    status             tinyint         not null default 1 comment '0-disabled 1-enabled',
    deleted            tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time        datetime        not null default current_timestamp comment 'create time',
    update_time        datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    key idx_status_receive (status, receive_start_time, receive_end_time)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'coupon template';

create table sms_coupon_template_scope
(
    id          bigint unsigned not null comment 'id',
    template_id bigint unsigned not null comment 'template id',
    scope_type  tinyint         not null comment '10-all 20-category 30-spu 40-sku',
    scope_id    bigint unsigned not null comment 'scope id',
    deleted     tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time datetime        not null default current_timestamp comment 'create time',
    update_time datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    key idx_template_id (template_id)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'coupon scope';

create table sms_user_coupon
(
    id               bigint unsigned not null comment 'id',
    template_id      bigint unsigned not null comment 'template id',
    user_id          bigint unsigned not null comment 'user id',
    coupon_code      varchar(64)     not null comment 'coupon code',
    coupon_name      varchar(64)     not null comment 'coupon name snapshot',
    coupon_type      tinyint         not null comment 'coupon type snapshot',
    threshold_amount decimal(10, 2)  not null default 0.00 comment 'threshold amount snapshot',
    discount_amount  decimal(10, 2)  not null default 0.00 comment 'discount amount snapshot',
    discount_rate    decimal(4, 2)            default null comment 'discount rate snapshot',
    scope_type       tinyint         not null comment 'scope type snapshot',
    status           tinyint         not null default 10 comment '10-unused 15-locked 20-used 30-expired',
    receive_time     datetime        not null comment 'receive time',
    valid_from       datetime        not null comment 'valid from',
    valid_to         datetime        not null comment 'valid to',
    use_time         datetime                 default null comment 'use time',
    order_no         varchar(64)              default null comment 'used order no',
    deleted          tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time      datetime        not null default current_timestamp comment 'create time',
    update_time      datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_coupon_code (coupon_code),
    key idx_user_status (user_id, status),
    key idx_template_user (template_id, user_id)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'user coupon';

create table sms_flash_sale_activity
(
    id          bigint unsigned not null comment 'activity id',
    name        varchar(64)     not null comment 'activity name',
    start_time  datetime        not null comment 'start time',
    end_time    datetime        not null comment 'end time',
    status      tinyint         not null default 1 comment '0-disabled 1-enabled',
    deleted     tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time datetime        not null default current_timestamp comment 'create time',
    update_time datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    key idx_status_time (status, start_time, end_time)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'flash sale activity';

create table sms_flash_sale_sku
(
    id             bigint unsigned not null comment 'id',
    activity_id    bigint unsigned not null comment 'activity id',
    sku_id         bigint unsigned not null comment 'sku id',
    original_price decimal(10, 2)  not null default 0.00 comment 'original price',
    discount_price decimal(10, 2)  not null default 0.00 comment 'discount price',
    activity_stock int             not null default 0 comment 'activity stock',
    locked_stock   int             not null default 0 comment 'locked stock',
    per_user_limit int             not null default 1 comment 'per user limit',
    sort           int             not null default 0 comment 'sort',
    deleted        tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time    datetime        not null default current_timestamp comment 'create time',
    update_time    datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    key idx_activity_id (activity_id),
    key idx_sku_id (sku_id)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'flash sale sku';

create table sms_flash_sale_order_record
(
    id             bigint unsigned not null comment 'id',
    order_no       varchar(64)     not null comment 'order no',
    activity_id    bigint unsigned not null comment 'activity id',
    sku_id         bigint unsigned not null comment 'sku id',
    quantity       int             not null default 0 comment 'locked quantity',
    discount_price decimal(10, 2)  not null default 0.00 comment 'locked discount price',
    status         tinyint         not null comment '10-locked 20-used 30-released',
    deleted        tinyint         not null default 0 comment 'logic delete 0-false 1-true',
    create_time    datetime        not null default current_timestamp comment 'create time',
    update_time    datetime        not null default current_timestamp on update current_timestamp comment 'update time',
    primary key (id),
    unique key uk_order_sku (order_no, sku_id),
    key idx_activity_id (activity_id)
) engine = InnoDB
  default charset = utf8mb4
  collate = utf8mb4_unicode_ci comment 'flash sale order lock record';
