package com.cloudedge.platform.product.service;

import com.cloudedge.platform.product.model.dto.BrandSaveRequest;
import com.cloudedge.platform.product.model.vo.BrandResponse;

import java.util.List;

public interface BrandService {

    BrandResponse createBrand(BrandSaveRequest request);

    BrandResponse updateBrand(Long brandId, BrandSaveRequest request);

    void deleteBrand(Long brandId);

    List<BrandResponse> listAdminBrands();

    List<BrandResponse> listEnabledBrands();
}
