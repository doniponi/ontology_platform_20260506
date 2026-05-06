package com.ontology.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.ontology.entity.ObjectTypeLayout;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ObjectTypeLayoutMapper extends BaseMapper<ObjectTypeLayout> {

    @Select("SELECT * FROM object_type_layouts WHERE project_id = #{projectId}")
    List<ObjectTypeLayout> selectByProjectId(@Param("projectId") String projectId);

    @Select("SELECT * FROM object_type_layouts WHERE project_id = #{projectId} AND object_type_id = #{objectTypeId}")
    ObjectTypeLayout selectByProjectIdAndObjectTypeId(@Param("projectId") String projectId, @Param("objectTypeId") String objectTypeId);
}
