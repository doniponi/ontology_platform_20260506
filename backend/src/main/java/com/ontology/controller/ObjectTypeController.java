package com.ontology.controller;

import com.ontology.entity.ObjectType;
import com.ontology.entity.ObjectTypeInterfaceMapping;
import com.ontology.entity.Property;
import com.ontology.service.InterfaceService;
import com.ontology.mapper.ObjectTypeMapper;
import com.ontology.mapper.PropertyMapper;
import com.ontology.service.OntologyService;
import com.ontology.service.RuleTemplateService;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/object-types")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class ObjectTypeController {

    private final ObjectTypeMapper objectTypeMapper;
    private final PropertyMapper propertyMapper;
    private final OntologyService ontologyService;
    private final RuleTemplateService ruleTemplateService;
    private final InterfaceService interfaceService;

    @PostMapping
    @Transactional
    public Map<String, Object> create(@RequestBody ObjectType objectType, @RequestParam(required = false) String projectId) {
        objectType.setProjectId(com.ontology.project.ProjectScope.normalize(projectId));
        objectType.setStatus("pending"); // 新建对象类型默认待审核

        // 防止循环引用：不能把自己或自己的后代设为自己的父对象
        if (objectType.getParentObjectType() != null && !objectType.getParentObjectType().isEmpty()) {
            if (objectType.getId() != null && isDescendant(objectType.getParentObjectType(), objectType.getId(), objectType.getProjectId())) {
                Map<String, Object> errorResult = new HashMap<>();
                errorResult.put("success", false);
                errorResult.put("error", "不能将子对象类型设置为其自身的父对象类型，会导致循环引用");
                return errorResult;
            }
        }

        objectTypeMapper.insert(objectType);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", ontologyService.buildOntologyData(objectType.getProjectId()));
        return result;
    }

    @PutMapping("/{id}")
    @Transactional
    public Map<String, Object> update(@PathVariable String id, @RequestBody ObjectType objectType, @RequestParam(required = false) String projectId) {
        objectType.setId(id);
        objectType.setProjectId(com.ontology.project.ProjectScope.normalize(projectId));

        // 防止循环引用：只在父对象类型真正发生改变时才校验
        String newParent = objectType.getParentObjectType();
        ObjectType existing = objectTypeMapper.selectById(id);
        String oldParent = existing != null ? existing.getParentObjectType() : null;
        boolean parentChanged = (newParent == null ? oldParent != null : !newParent.equals(oldParent));
        if (parentChanged && newParent != null && !newParent.isEmpty()) {
            if (isDescendant(newParent, id, objectType.getProjectId())) {
                Map<String, Object> errorResult = new HashMap<>();
                errorResult.put("success", false);
                errorResult.put("error", "不能将子对象类型设置为其自身的父对象类型，会导致循环引用");
                return errorResult;
            }
        }

        // 使用 UpdateWrapper 显式更新，确保 parent_object_type 字段一定会被写入数据库
        UpdateWrapper<ObjectType> wrapper = new UpdateWrapper<>();
        wrapper.eq("id", id);
        if (objectType.getName() != null) wrapper.set("name", objectType.getName());
        if (objectType.getDescription() != null) wrapper.set("description", objectType.getDescription());
        if (objectType.getBackingDataset() != null) wrapper.set("backing_dataset", objectType.getBackingDataset());
        if (objectType.getIcon() != null) wrapper.set("icon", objectType.getIcon());
        if (objectType.getIndustryId() != null) wrapper.set("industry_id", objectType.getIndustryId());
        wrapper.set("parent_object_type", objectType.getParentObjectType());
        if (objectType.getShowParentLink() != null) wrapper.set("show_parent_link", objectType.getShowParentLink() ? 1 : 0);
        if (objectType.getObjectTypeCategory() != null) wrapper.set("object_type_category", objectType.getObjectTypeCategory());
        objectTypeMapper.update(null, wrapper);

        ObjectType updated = objectTypeMapper.selectById(id);
        if (updated != null && "active".equalsIgnoreCase(updated.getStatus())) {
            ruleTemplateService.ensureObjectTypeRules(updated);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", ontologyService.buildOntologyData(objectType.getProjectId()));
        return result;
    }

    @DeleteMapping("/{id}")
    @Transactional
    public Map<String, Object> delete(@PathVariable String id, @RequestParam(required = false) String projectId) {
        projectId = com.ontology.project.ProjectScope.normalize(projectId);

        // 校验：只有当该对象类型没有子对象类型时才可以删除
        int childCount = objectTypeMapper.countChildren(id);
        if (childCount > 0) {
            Map<String, Object> errorResult = new HashMap<>();
            errorResult.put("success", false);
            errorResult.put("error", "该对象类型下存在 " + childCount + " 个子对象类型，请先删除所有子对象类型后再删除");
            return errorResult;
        }

        ruleTemplateService.deleteObjectTypeRuleArtifacts(id);
        objectTypeMapper.deleteById(id);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", ontologyService.buildOntologyData(projectId));
        return result;
    }

    @PostMapping("/{objectTypeId}/properties")
    @Transactional
    public Map<String, Object> addProperty(@PathVariable String objectTypeId, @RequestBody Property property, @RequestParam(required = false) String projectId) {
        try {
            projectId = com.ontology.project.ProjectScope.normalize(projectId);
            property.setObjectTypeId(objectTypeId);
            property.setProjectId(projectId);
            propertyMapper.insert(property);
            ObjectType objectType = objectTypeMapper.selectById(objectTypeId);
            if (objectType != null && "active".equalsIgnoreCase(objectType.getStatus())) {
                ruleTemplateService.ensureObjectTypeRules(objectType);
            }
            Map<String, Object> result = new HashMap<>();
            result.put("success", true);
            result.put("data", ontologyService.buildOntologyData(projectId));
            return result;
        } catch (org.springframework.dao.DuplicateKeyException e) {
            Map<String, Object> errorResult = new HashMap<>();
            errorResult.put("success", false);
            errorResult.put("error", "属性ID '" + property.getId() + "' 已存在，请更换一个唯一的属性ID。");
            return errorResult;
        }
    }

    @DeleteMapping("/{objectTypeId}/properties/{propId}")
    @Transactional
    public Map<String, Object> deleteProperty(@PathVariable String objectTypeId, @PathVariable String propId, @RequestParam(required = false) String projectId) {
        projectId = com.ontology.project.ProjectScope.normalize(projectId);
        Property existing = propertyMapper.selectOne(
            new QueryWrapper<Property>().eq("object_type_id", objectTypeId).eq("id", propId)
        );
        if (existing != null) {
            propertyMapper.deleteById(existing.getAutoId());
        }
        ObjectType objectType = objectTypeMapper.selectById(objectTypeId);
        if (objectType != null && "active".equalsIgnoreCase(objectType.getStatus())) {
            ruleTemplateService.ensureObjectTypeRules(objectType);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", ontologyService.buildOntologyData(projectId));
        return result;
    }

    @PutMapping("/{objectTypeId}/properties/{propId}")
    @Transactional
    public Map<String, Object> updateProperty(@PathVariable String objectTypeId, @PathVariable String propId, @RequestBody Property property, @RequestParam(required = false) String projectId) {
        projectId = com.ontology.project.ProjectScope.normalize(projectId);
        Property existing = propertyMapper.selectOne(
            new QueryWrapper<Property>().eq("object_type_id", objectTypeId).eq("id", propId)
        );
        if (existing != null) {
            property.setAutoId(existing.getAutoId());
            property.setId(propId);
            property.setObjectTypeId(objectTypeId);
            property.setProjectId(projectId);
            propertyMapper.updateById(property);
        }
        ObjectType objectType = objectTypeMapper.selectById(objectTypeId);
        if (objectType != null && "active".equalsIgnoreCase(objectType.getStatus())) {
            ruleTemplateService.ensureObjectTypeRules(objectType);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", ontologyService.buildOntologyData(projectId));
        return result;
    }

    @GetMapping("/{objectTypeId}/interfaces")
    public Map<String, Object> listImplementedInterfaces(@PathVariable String objectTypeId, @RequestParam(required = false) String projectId) {
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("interfaces", interfaceService.listObjectTypeInterfaceMappings(objectTypeId, projectId));
        return result;
    }

    @PostMapping("/{objectTypeId}/interfaces")
    @Transactional
    public Map<String, Object> createImplementedInterface(
            @PathVariable String objectTypeId,
            @RequestBody ObjectTypeInterfaceMapping mapping,
            @RequestParam(required = false) String projectId) {
        projectId = com.ontology.project.ProjectScope.normalize(projectId);
        interfaceService.saveObjectTypeInterfaceMapping(objectTypeId, mapping, projectId);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", ontologyService.buildOntologyData(projectId));
        return result;
    }

    @PutMapping("/{objectTypeId}/interfaces/{mappingId}")
    @Transactional
    public Map<String, Object> updateImplementedInterface(
            @PathVariable String objectTypeId,
            @PathVariable String mappingId,
            @RequestBody ObjectTypeInterfaceMapping mapping,
            @RequestParam(required = false) String projectId) {
        projectId = com.ontology.project.ProjectScope.normalize(projectId);
        mapping.setId(mappingId);
        interfaceService.saveObjectTypeInterfaceMapping(objectTypeId, mapping, projectId);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", ontologyService.buildOntologyData(projectId));
        return result;
    }

    @DeleteMapping("/{objectTypeId}/interfaces/{mappingId}")
    @Transactional
    public Map<String, Object> deleteImplementedInterface(
            @PathVariable String objectTypeId,
            @PathVariable String mappingId,
            @RequestParam(required = false) String projectId) {
        projectId = com.ontology.project.ProjectScope.normalize(projectId);
        interfaceService.deleteObjectTypeInterfaceMapping(objectTypeId, mappingId, projectId);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", ontologyService.buildOntologyData(projectId));
        return result;
    }

    // ── Helper Methods for Sub-Object-Type Hierarchy ──────────────────────────

    /**
     * 获取对象类型的层级深度（一级 = 1，二级 = 2，以此类推）
     */
    private int getDepth(String objectTypeId) {
        int depth = 1;
        ObjectType ot = objectTypeMapper.selectById(objectTypeId);
        while (ot != null && ot.getParentObjectType() != null && !ot.getParentObjectType().isEmpty()) {
            depth++;
            if (depth > 100) break; // 安全上限，防止异常数据导致死循环
            ot = objectTypeMapper.selectById(ot.getParentObjectType());
        }
        return depth;
    }

    /**
     * 判断 candidateId 是否是 ancestorId 的后代（包括直接子对象类型和间接子对象类型）
     */
    private boolean isDescendant(String ancestorId, String candidateId, String projectId) {
        if (ancestorId == null || candidateId == null || ancestorId.equals(candidateId)) {
            return ancestorId != null && ancestorId.equals(candidateId);
        }
        java.util.List<ObjectType> children = objectTypeMapper.selectChildren(ancestorId, projectId);
        for (ObjectType child : children) {
            if (child.getId().equals(candidateId) || isDescendant(child.getId(), candidateId, projectId)) {
                return true;
            }
        }
        return false;
    }
}
