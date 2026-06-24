package com.cloudedge.platform.user.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class UserAddressSaveRequest {

    @NotBlank(message = "收货人不能为空")
    @Size(max = 64, message = "收货人长度不能超过64位")
    private String receiverName;

    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1\\d{10}$", message = "手机号格式不正确")
    private String receiverMobile;

    @Size(max = 32, message = "省编码长度不能超过32位")
    private String provinceCode;

    @Size(max = 32, message = "省名称长度不能超过32位")
    private String provinceName;

    @Size(max = 32, message = "市编码长度不能超过32位")
    private String cityCode;

    @Size(max = 32, message = "市名称长度不能超过32位")
    private String cityName;

    @Size(max = 32, message = "区编码长度不能超过32位")
    private String districtCode;

    @Size(max = 32, message = "区名称长度不能超过32位")
    private String districtName;

    @NotBlank(message = "详细地址不能为空")
    @Size(max = 255, message = "详细地址长度不能超过255位")
    private String detailAddress;

    @Size(max = 16, message = "邮编长度不能超过16位")
    private String postalCode;

    private Boolean defaultAddress;
}
