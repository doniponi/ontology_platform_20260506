package com.ontology.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.ontology.entity.ObjectTypeLayout;
import com.ontology.mapper.ObjectTypeLayoutMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/object-type-layouts")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class ObjectTypeLayoutController {

    private final ObjectTypeLayoutMapper objectTypeLayoutMapper;

    @GetMapping
    public Map<String, Object> list(@RequestParam(required = false) String projectId) {
        projectId = com.ontology.project.ProjectScope.normalize(projectId);
        List<ObjectTypeLayout> layouts = objectTypeLayoutMapper.selectByProjectId(projectId);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", layouts);
        return result;
    }

    @PostMapping("/batch")
    public Map<String, Object> saveBatch(
            @RequestBody List<ObjectTypeLayout> layouts,
            @RequestParam(required = false) String projectId) {
        projectId = com.ontology.project.ProjectScope.normalize(projectId);

        for (ObjectTypeLayout layout : layouts) {
            layout.setProjectId(projectId);
            QueryWrapper<ObjectTypeLayout> queryWrapper = new QueryWrapper<>();
            queryWrapper.eq("project_id", projectId)
                       .eq("object_type_id", layout.getObjectTypeId());
            ObjectTypeLayout existing = objectTypeLayoutMapper.selectOne(queryWrapper);
            if (existing != null) {
                // Use UpdateWrapper to explicitly set only provided fields
                // This avoids updateById issues with newly added columns (width/height)
                UpdateWrapper<ObjectTypeLayout> updateWrapper = new UpdateWrapper<>();
                updateWrapper.eq("id", existing.getId());
                if (layout.getX() != null) {
                    updateWrapper.set("x", layout.getX());
                }
                if (layout.getY() != null) {
                    updateWrapper.set("y", layout.getY());
                }
                if (layout.getWidth() != null) {
                    updateWrapper.set("width", layout.getWidth());
                }
                if (layout.getHeight() != null) {
                    updateWrapper.set("height", layout.getHeight());
                }
                objectTypeLayoutMapper.update(null, updateWrapper);
            } else {
                objectTypeLayoutMapper.insert(layout);
            }
        }

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        return result;
    }
}
