package com.cloudedge.platform.user.model.vo;


import lombok.Builder;
import lombok.Data;

@Builder
@Data
public class UserAddressResponse {
    private Long id;
    private String receiverName;
    private String receiverMobile;
    private String provinceCode;
    private String provinceName;
    private String cityCode;
    private String cityName;
    private String districtCode;
    private String districtName;
    private String detailAddress;
    private String postalCode;
    private Boolean defaultAddress;
}
