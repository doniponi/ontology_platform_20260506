package com.ontology.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ontology.entity.NewsMultisource;
import com.ontology.mapper.NewsMultisourceMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/news")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class NewsMultisourceController {

    private final NewsMultisourceMapper newsMapper;

    @GetMapping
    public Map<String, Object> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        Page<NewsMultisource> pageParam = new Page<>(page, size);
        IPage<NewsMultisource> result = newsMapper.selectPage(pageParam, null);

        Map<String, Object> data = new HashMap<>();
        data.put("records", result.getRecords());
        data.put("total", result.getTotal());
        data.put("page", result.getCurrent());
        data.put("size", result.getSize());
        data.put("totalPages", result.getPages());

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("data", data);
        return response;
    }

    @PostMapping
    public Map<String, Object> create(@RequestBody NewsMultisource news) {
        newsMapper.insert(news);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("data", news);
        return response;
    }
}
