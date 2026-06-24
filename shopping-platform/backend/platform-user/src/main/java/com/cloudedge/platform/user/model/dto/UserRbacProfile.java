package com.cloudedge.platform.user.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Collections;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserRbacProfile {

    @Builder.Default
    private List<String> roles = Collections.emptyList();

    @Builder.Default
    private List<String> permissions = Collections.emptyList();
}
