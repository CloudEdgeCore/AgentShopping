package com.cloudedge.platform.logging;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.ArrayList;
import java.util.List;

@Data
@ConfigurationProperties(prefix = "platform.logging")
public class PlatformLoggingProperties {

    private String environment = "local";

    private String filePath = "${user.dir}/runtime-logs";

    private Trace trace = new Trace();

    private Access access = new Access();

    @Data
    public static class Trace {

        private boolean enabled = true;

        private String requestHeader = "X-Trace-Id";

        private boolean responseHeaderEnabled = true;
    }

    @Data
    public static class Access {

        private boolean enabled = true;

        private long slowThresholdMs = 1500L;

        private List<String> excludePaths = new ArrayList<>(List.of(
                "/actuator/health",
                "/favicon.ico"
        ));
    }
}
