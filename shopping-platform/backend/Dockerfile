FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /build

COPY pom.xml .
COPY platform-app/pom.xml platform-app/
COPY platform-common/pom.xml platform-common/
COPY platform-security/pom.xml platform-security/
COPY platform-infrastructure/pom.xml platform-infrastructure/
COPY platform-user/pom.xml platform-user/
COPY platform-product/pom.xml platform-product/
COPY platform-search/pom.xml platform-search/
COPY platform-cart/pom.xml platform-cart/
COPY platform-order/pom.xml platform-order/
COPY platform-inventory/pom.xml platform-inventory/
COPY platform-marketing/pom.xml platform-marketing/
COPY platform-seckill/pom.xml platform-seckill/
COPY platform-payment/pom.xml platform-payment/
COPY platform-job/pom.xml platform-job/

RUN mvn dependency:go-offline -B

COPY . .
RUN mvn package -pl platform-app -am -DskipTests -B

FROM eclipse-temurin:17-jre

WORKDIR /app

COPY --from=build /build/platform-app/target/platform-app-1.0.0-SNAPSHOT.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
