package com.cloudedge.platform.inventory.model.vo;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class PageResponse<T> {

    private long current;
    private long size;
    private long total;
    private List<T> records;
}
