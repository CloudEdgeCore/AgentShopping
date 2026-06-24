package com.cloudedge.platform.user.model.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class RegisterRequest {

    @NotBlank(message = "username cannot be blank")
    @Size(min = 4, max = 32, message = "username length must be between 4 and 32")
    private String username;

    @NotBlank(message = "password cannot be blank")
    @Size(min = 6, max = 32, message = "password length must be between 6 and 32")
    private String password;

    @Size(max = 64, message = "nickname length cannot exceed 64")
    private String nickname;

    @Pattern(regexp = "^1\\d{10}$", message = "mobile format is invalid")
    private String mobile;

    @Email(message = "email format is invalid")
    @Size(max = 128, message = "email length cannot exceed 128")
    private String email;

    @Size(max = 255, message = "avatar url length cannot exceed 255")
    private String avatarUrl;

    @Min(value = 0, message = "gender value is invalid")
    @Max(value = 2, message = "gender value is invalid")
    private Integer gender;
}
