package com.cloudedge.platform.search.model.document;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(indexName = "spu_search_v1")
public class ProductSearchDocument {

    @Id
    private Long spuId;

    @Field(type = FieldType.Text)
    private String spuName;

    @Field(type = FieldType.Text)
    private String subtitle;

    @Field(type = FieldType.Keyword)
    private String coverImage;

    @Field(type = FieldType.Long)
    private Long categoryId;

    @Field(type = FieldType.Text)
    private String categoryName;

    @Field(type = FieldType.Long)
    private Long brandId;

    @Field(type = FieldType.Text)
    private String brandName;

    @Field(type = FieldType.Double)
    private BigDecimal minSalePrice;

    @Field(type = FieldType.Double)
    private BigDecimal maxSalePrice;

    @Field(type = FieldType.Integer)
    private Integer publishStatus;

    @Field(type = FieldType.Integer)
    private Integer sort;

    @Field(type = FieldType.Date)
    private LocalDate updateTime;
}
