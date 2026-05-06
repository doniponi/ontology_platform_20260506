package com.ontology.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("object_type_layouts")
public class ObjectTypeLayout {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String projectId;

    private String objectTypeId;

    private Double x;

    private Double y;

    private Double width;

    private Double height;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
