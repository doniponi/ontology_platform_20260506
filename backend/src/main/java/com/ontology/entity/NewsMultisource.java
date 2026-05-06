package com.ontology.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("news_multisource")
public class NewsMultisource {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String texttitle;

    private LocalDateTime entrytime;

    private String medianame;

    private String authors;

    private String abs;

    private String originalurl;
}
