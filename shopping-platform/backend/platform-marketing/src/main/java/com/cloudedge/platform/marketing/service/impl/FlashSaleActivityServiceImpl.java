package com.cloudedge.platform.marketing.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.cloudedge.platform.exception.BizException;
import com.cloudedge.platform.marketing.entity.FlashSaleActivityDO;
import com.cloudedge.platform.marketing.entity.FlashSaleSkuDO;
import com.cloudedge.platform.marketing.enums.FlashSaleStatusEnum;
import com.cloudedge.platform.marketing.exception.MarketingErrorCode;
import com.cloudedge.platform.marketing.mapper.FlashSaleActivityMapper;
import com.cloudedge.platform.marketing.mapper.FlashSaleSkuMapper;
import com.cloudedge.platform.marketing.model.dto.FlashSaleActivityPageQueryRequest;
import com.cloudedge.platform.marketing.model.dto.FlashSaleActivitySaveRequest;
import com.cloudedge.platform.marketing.model.dto.FlashSaleSkuSaveRequest;
import com.cloudedge.platform.marketing.model.vo.FlashSaleActivityResponse;
import com.cloudedge.platform.marketing.model.vo.FlashSaleSkuResponse;
import com.cloudedge.platform.marketing.model.vo.PageResponse;
import com.cloudedge.platform.marketing.model.vo.SkuDiscountResponse;
import com.cloudedge.platform.marketing.service.FlashSaleActivityService;
import com.cloudedge.platform.marketing.support.MarketingAdminSupport;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class FlashSaleActivityServiceImpl implements FlashSaleActivityService {

    @Autowired
    private FlashSaleActivityMapper flashSaleActivityMapper;

    @Autowired
    private FlashSaleSkuMapper flashSaleSkuMapper;

    @Autowired
    private MarketingAdminSupport marketingAdminSupport;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public FlashSaleActivityResponse createActivity(FlashSaleActivitySaveRequest request) {
        marketingAdminSupport.requireAdminUser();
        validateActivityRequest(request);

        FlashSaleActivityDO activityDO = new FlashSaleActivityDO();
        activityDO.setName(request.getName().trim());
        activityDO.setStartTime(request.getStartTime());
        activityDO.setEndTime(request.getEndTime());
        activityDO.setStatus(request.getStatus());
        activityDO.setDeleted(0);
        flashSaleActivityMapper.insert(activityDO);

        saveActivityItems(activityDO.getId(), request.getItems());

        return getActivityDetail(activityDO.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public FlashSaleActivityResponse updateActivity(Long activityId, FlashSaleActivitySaveRequest request) {
        marketingAdminSupport.requireAdminUser();
        validateActivityRequest(request);

        FlashSaleActivityDO activityDO = getActivityOrThrow(activityId);
        activityDO.setName(request.getName().trim());
        activityDO.setStartTime(request.getStartTime());
        activityDO.setEndTime(request.getEndTime());
        activityDO.setStatus(request.getStatus());
        flashSaleActivityMapper.updateById(activityDO);

        flashSaleSkuMapper.delete(Wrappers.<FlashSaleSkuDO>lambdaQuery()
                .eq(FlashSaleSkuDO::getActivityId, activityId));
        saveActivityItems(activityId, request.getItems());

        return getActivityDetail(activityId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteActivity(Long activityId) {
        marketingAdminSupport.requireAdminUser();
        getActivityOrThrow(activityId);
        flashSaleSkuMapper.delete(Wrappers.<FlashSaleSkuDO>lambdaQuery()
                .eq(FlashSaleSkuDO::getActivityId, activityId));
        flashSaleActivityMapper.deleteById(activityId);
    }

    @Override
    public PageResponse<FlashSaleActivityResponse> pageActivities(FlashSaleActivityPageQueryRequest request) {
        marketingAdminSupport.requireAdminUser();

        Page<FlashSaleActivityDO> page = flashSaleActivityMapper.selectPage(
                new Page<>(request.getCurrent(), request.getSize()),
                Wrappers.<FlashSaleActivityDO>lambdaQuery()
                        .eq(request.getStatus() != null, FlashSaleActivityDO::getStatus, request.getStatus())
                        .orderByDesc(FlashSaleActivityDO::getCreateTime)
                        .orderByDesc(FlashSaleActivityDO::getId)
        );

        List<FlashSaleActivityResponse> records = page.getRecords().stream()
                .map(activity -> FlashSaleActivityResponse.builder()
                        .id(activity.getId())
                        .name(activity.getName())
                        .startTime(activity.getStartTime())
                        .endTime(activity.getEndTime())
                        .status(activity.getStatus())
                        .items(Collections.emptyList())
                        .build())
                .toList();

        return PageResponse.<FlashSaleActivityResponse>builder()
                .current(page.getCurrent())
                .size(page.getSize())
                .total(page.getTotal())
                .records(records)
                .build();
    }

    @Override
    public FlashSaleActivityResponse getActivityDetail(Long activityId) {
        marketingAdminSupport.requireAdminUser();
        FlashSaleActivityDO activityDO = getActivityOrThrow(activityId);
        return buildActivityResponse(activityDO, listActivityItems(activityId));
    }

    @Override
    public List<SkuDiscountResponse> listActiveDiscounts(List<Long> skuIds) {
        LocalDateTime now = LocalDateTime.now();
        List<FlashSaleActivityDO> activityList = flashSaleActivityMapper.selectList(Wrappers.<FlashSaleActivityDO>lambdaQuery()
                .eq(FlashSaleActivityDO::getStatus, FlashSaleStatusEnum.ENABLED.getCode())
                .le(FlashSaleActivityDO::getStartTime, now)
                .ge(FlashSaleActivityDO::getEndTime, now));

        if (activityList.isEmpty()) {
            return Collections.emptyList();
        }

        Map<Long, FlashSaleActivityDO> activityMap = activityList.stream()
                .collect(Collectors.toMap(FlashSaleActivityDO::getId, item -> item));

        List<Long> activityIds = activityList.stream().map(FlashSaleActivityDO::getId).toList();
        List<FlashSaleSkuDO> skuList = flashSaleSkuMapper.selectList(Wrappers.<FlashSaleSkuDO>lambdaQuery()
                .in(FlashSaleSkuDO::getActivityId, activityIds)
                .in(skuIds != null && !skuIds.isEmpty(), FlashSaleSkuDO::getSkuId, skuIds)
                .gt(FlashSaleSkuDO::getActivityStock, 0)
                .orderByAsc(FlashSaleSkuDO::getSort)
                .orderByAsc(FlashSaleSkuDO::getId));

        return skuList.stream()
                .collect(Collectors.groupingBy(FlashSaleSkuDO::getSkuId))
                .values()
                .stream()
                .map(items -> items.stream().min(Comparator.comparing(FlashSaleSkuDO::getDiscountPrice)).orElse(null))
                .filter(item -> item != null && activityMap.containsKey(item.getActivityId()))
                .map(item -> {
                    FlashSaleActivityDO activityDO = activityMap.get(item.getActivityId());
                    return SkuDiscountResponse.builder()
                            .skuId(item.getSkuId())
                            .activityId(activityDO.getId())
                            .activityName(activityDO.getName())
                            .originalPrice(item.getOriginalPrice())
                            .discountPrice(item.getDiscountPrice())
                            .activityStock(item.getActivityStock())
                            .lockedStock(item.getLockedStock())
                            .perUserLimit(item.getPerUserLimit())
                            .startTime(activityDO.getStartTime())
                            .endTime(activityDO.getEndTime())
                            .build();
                })
                .toList();
    }

    private FlashSaleActivityDO getActivityOrThrow(Long activityId) {
        FlashSaleActivityDO activityDO = flashSaleActivityMapper.selectById(activityId);
        if (activityDO == null) {
            throw new BizException(MarketingErrorCode.FLASH_SALE_ACTIVITY_NOT_FOUND);
        }
        return activityDO;
    }

    private List<FlashSaleSkuResponse> listActivityItems(Long activityId) {
        return flashSaleSkuMapper.selectList(Wrappers.<FlashSaleSkuDO>lambdaQuery()
                        .eq(FlashSaleSkuDO::getActivityId, activityId)
                        .orderByAsc(FlashSaleSkuDO::getSort)
                        .orderByAsc(FlashSaleSkuDO::getId))
                .stream()
                .map(this::buildSkuResponse)
                .toList();
    }

    private FlashSaleActivityResponse buildActivityResponse(FlashSaleActivityDO activityDO,
                                                            List<FlashSaleSkuResponse> items) {
        return FlashSaleActivityResponse.builder()
                .id(activityDO.getId())
                .name(activityDO.getName())
                .startTime(activityDO.getStartTime())
                .endTime(activityDO.getEndTime())
                .status(activityDO.getStatus())
                .items(items)
                .build();
    }

    private FlashSaleSkuResponse buildSkuResponse(FlashSaleSkuDO item) {
        return FlashSaleSkuResponse.builder()
                .skuId(item.getSkuId())
                .originalPrice(item.getOriginalPrice())
                .discountPrice(item.getDiscountPrice())
                .activityStock(item.getActivityStock())
                .lockedStock(item.getLockedStock())
                .perUserLimit(item.getPerUserLimit())
                .sort(item.getSort())
                .build();
    }

    private void saveActivityItems(Long activityId, List<FlashSaleSkuSaveRequest> items) {
        for (FlashSaleSkuSaveRequest item : items) {
            FlashSaleSkuDO skuDO = new FlashSaleSkuDO();
            skuDO.setActivityId(activityId);
            skuDO.setSkuId(item.getSkuId());
            skuDO.setOriginalPrice(item.getOriginalPrice());
            skuDO.setDiscountPrice(item.getDiscountPrice());
            skuDO.setActivityStock(item.getActivityStock());
            skuDO.setLockedStock(0);
            skuDO.setPerUserLimit(item.getPerUserLimit());
            skuDO.setSort(item.getSort() == null ? 0 : item.getSort());
            skuDO.setDeleted(0);
            flashSaleSkuMapper.insert(skuDO);
        }
    }

    private void validateActivityRequest(FlashSaleActivitySaveRequest request) {
        if (!request.getEndTime().isAfter(request.getStartTime())) {
            throw new BizException(MarketingErrorCode.INVALID_ACTIVITY_TIME);
        }
        for (FlashSaleSkuSaveRequest item : request.getItems()) {
            if (item.getDiscountPrice().compareTo(item.getOriginalPrice()) >= 0
                    || item.getActivityStock() <= 0
                    || item.getPerUserLimit() <= 0) {
                throw new BizException(MarketingErrorCode.INVALID_FLASH_SALE_ITEM);
            }
            if (item.getOriginalPrice().compareTo(BigDecimal.ZERO) <= 0
                    || item.getDiscountPrice().compareTo(BigDecimal.ZERO) <= 0) {
                throw new BizException(MarketingErrorCode.INVALID_FLASH_SALE_ITEM);
            }
        }
    }
}
