package com.cloudedge.platform.app;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication(scanBasePackages = "com.cloudedge.platform")
@ConfigurationPropertiesScan("com.cloudedge.platform")
@EnableScheduling
@MapperScan({
        "com.cloudedge.platform.user.mapper",
        "com.cloudedge.platform.product.mapper",
        "com.cloudedge.platform.cart.mapper",
        "com.cloudedge.platform.inventory.mapper",
        "com.cloudedge.platform.order.mapper",
        "com.cloudedge.platform.payment.mapper",
        "com.cloudedge.platform.marketing.mapper"
})
public class PlatformApplication {
    public static void main(String[] args) {
        SpringApplication.run(PlatformApplication.class);
    }
}
