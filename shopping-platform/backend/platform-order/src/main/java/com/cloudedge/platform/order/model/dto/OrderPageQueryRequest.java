package com.cloudedge.platform.order.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

public class OrderPageQueryRequest {

    @Min(value = 1, message = "current must be greater than 0")
    private long current = 1;

    @Min(value = 1, message = "size must be greater than 0")
    @Max(value = 100, message = "size cannot exceed 100")
    private long size = 10;

    private Integer status;

    public long getCurrent() {
        return current;
    }

    public void setCurrent(long current) {
        this.current = current;
    }

    public long getSize() {
        return size;
    }

    public void setSize(long size) {
        this.size = size;
    }

    public Integer getStatus() {
        return status;
    }

    public void setStatus(Integer status) {
        this.status = status;
    }
}
