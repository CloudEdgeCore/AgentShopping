package com.cloudedge.platform.marketing.controller;

import com.cloudedge.platform.marketing.model.vo.SkuDiscountResponse;
import com.cloudedge.platform.marketing.service.FlashSaleActivityService;
import com.cloudedge.platform.response.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/marketing/flash-sale")
public class FlashSalePublicController {

    @Autowired
    private FlashSaleActivityService flashSaleActivityService;

    @GetMapping("/sku-discounts")
    public Result<List<SkuDiscountResponse>> listActiveDiscounts(@RequestParam(required = false) List<Long> skuIds) {
        return Result.success(flashSaleActivityService.listActiveDiscounts(skuIds));
    }
}
