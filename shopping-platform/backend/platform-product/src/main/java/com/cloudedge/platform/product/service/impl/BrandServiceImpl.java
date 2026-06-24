package com.cloudedge.platform.product.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.product.entity.BrandDO;
import com.cloudedge.platform.product.entity.ProductSpuDO;
import com.cloudedge.platform.product.enums.ProductDataStatusEnum;
import com.cloudedge.platform.product.exception.ProductErrorCode;
import com.cloudedge.platform.product.mapper.BrandMapper;
import com.cloudedge.platform.product.mapper.ProductSpuMapper;
import com.cloudedge.platform.product.model.dto.BrandSaveRequest;
import com.cloudedge.platform.product.model.vo.BrandResponse;
import com.cloudedge.platform.product.service.BrandService;
import com.cloudedge.platform.product.support.ProductAdminSupport;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class BrandServiceImpl implements BrandService {

    @Autowired
    private BrandMapper brandMapper;

    @Autowired
    private ProductSpuMapper productSpuMapper;

    @Autowired
    private ProductAdminSupport productAdminSupport;

    @Override
    public BrandResponse createBrand(BrandSaveRequest request) {
        productAdminSupport.requireAdminUser();
        validateDuplicateBrand(request.getName(), null);

        BrandDO brandDO = new BrandDO();
        brandDO.setName(request.getName().trim());
        brandDO.setLogoUrl(trimToNull(request.getLogoUrl()));
        brandDO.setDescription(trimToNull(request.getDescription()));
        brandDO.setSort(request.getSort());
        brandDO.setStatus(request.getStatus());
        brandDO.setDeleted(0);

        brandMapper.insert(brandDO);
        return buildResponse(brandDO);
    }

    @Override
    public BrandResponse updateBrand(Long brandId, BrandSaveRequest request) {
        productAdminSupport.requireAdminUser();
        BrandDO brandDO = getBrandOrThrow(brandId);
        validateDuplicateBrand(request.getName(), brandId);

        brandDO.setName(request.getName().trim());
        brandDO.setLogoUrl(trimToNull(request.getLogoUrl()));
        brandDO.setDescription(trimToNull(request.getDescription()));
        brandDO.setSort(request.getSort());
        brandDO.setStatus(request.getStatus());

        brandMapper.updateById(brandDO);
        return buildResponse(brandDO);
    }

    @Override
    public void deleteBrand(Long brandId) {
        productAdminSupport.requireAdminUser();
        getBrandOrThrow(brandId);

        Long relatedProductCount = productSpuMapper.selectCount(
                Wrappers.<ProductSpuDO>lambdaQuery()
                        .eq(ProductSpuDO::getBrandId, brandId)
        );
        if (relatedProductCount != null && relatedProductCount > 0) {
            throw new BizException(ProductErrorCode.BRAND_IN_USE);
        }
        brandMapper.deleteById(brandId);
    }

    @Override
    public List<BrandResponse> listAdminBrands() {
        productAdminSupport.requireAdminUser();
        return listBrands(null);
    }

    @Override
    public List<BrandResponse> listEnabledBrands() {
        return listBrands(ProductDataStatusEnum.ENABLED.getCode());
    }

    private List<BrandResponse> listBrands(Integer status) {
        var wrapper = Wrappers.<BrandDO>lambdaQuery()
                .orderByAsc(BrandDO::getSort)
                .orderByAsc(BrandDO::getId);
        if (status != null) {
            wrapper.eq(BrandDO::getStatus, status);
        }
        return brandMapper.selectList(wrapper).stream()
                .map(this::buildResponse)
                .toList();
    }

    private BrandDO getBrandOrThrow(Long brandId) {
        BrandDO brandDO = brandMapper.selectById(brandId);
        if (brandDO == null) {
            throw new BizException(ProductErrorCode.BRAND_NOT_FOUND);
        }
        return brandDO;
    }

    private void validateDuplicateBrand(String name, Long excludeId) {
        var wrapper = Wrappers.<BrandDO>lambdaQuery()
                .eq(BrandDO::getName, name.trim());
        if (excludeId != null) {
            wrapper.ne(BrandDO::getId, excludeId);
        }
        Long count = brandMapper.selectCount(wrapper);
        if (count != null && count > 0) {
            throw new BizException(ProductErrorCode.BRAND_NAME_EXISTS);
        }
    }

    private BrandResponse buildResponse(BrandDO brandDO) {
        return BrandResponse.builder()
                .id(brandDO.getId())
                .name(brandDO.getName())
                .logoUrl(brandDO.getLogoUrl())
                .description(brandDO.getDescription())
                .sort(brandDO.getSort())
                .status(brandDO.getStatus())
                .build();
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
