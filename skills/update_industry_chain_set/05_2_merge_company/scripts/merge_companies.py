#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
产业链图谱企业合并脚本

功能：
1. 从原始图谱提取原有企业数据
2. 从新增企业清单解析新增企业
3. 将企业合并到 V2 图谱骨架中
4. 输出 V3 完整图谱

用法：
python merge_companies.py \
  --original ./图谱/intermediate/02_original_graph.md \
  --skeleton ./图谱/intermediate/04_v2_optimized.md \
  --new-companies ./图谱/intermediate/05_new_companies.md \
  --output ./图谱/intermediate/05_v3_with_companies.md
"""

import argparse
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from datetime import datetime


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='合并企业数据到产业链图谱')
    parser.add_argument('--original', required=True, help='原始图谱文件路径')
    parser.add_argument('--skeleton', required=True, help='V2骨架图谱文件路径')
    parser.add_argument('--new-companies', required=True, help='新增企业清单文件路径')
    parser.add_argument('--output', required=True, help='输出文件路径')
    return parser.parse_args()


def extract_companies_from_graph(content: str) -> Dict[str, List[str]]:
    """
    从图谱内容中提取企业数据
    
    返回: {node_path: [company1, company2, ...]}
    """
    companies_map = defaultdict(list)
    lines = content.split('\n')
    
    current_path = []  # 当前节点路径
    last_node_level = 0  # 上一个节点的层级
    last_node_line_idx = -1  # 上一个节点的行号
    
    for i, line in enumerate(lines):
        # 检测标题层级
        header_match = re.match(r'^(#{1,7})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            node_name = header_match.group(2).strip()
            
            # 更新路径
            if level <= len(current_path):
                current_path = current_path[:level-1]
            current_path.append(node_name)
            
            last_node_level = level
            last_node_line_idx = i
            
        # 检测企业行（**企业列表**）
        elif line.strip().startswith('**') and line.strip().endswith('**'):
            # 只处理四级及以下节点的企业
            if last_node_level >= 4 and last_node_line_idx >= 0:
                # 提取企业列表
                company_line = line.strip()[2:-2]  # 去掉 ** **
                companies = parse_company_line(company_line)
                
                if companies:
                    node_path = ' > '.join(current_path)
                    companies_map[node_path] = companies
    
    return dict(companies_map)


def parse_company_line(line: str) -> List[str]:
    """
    解析企业行，提取企业列表
    
    输入: "企业1 (企业1全称) & 企业2 (企业2全称)"
    输出: ["企业1 (企业1全称)", "企业2 (企业2全称)"]
    """
    companies = []
    
    # 按 & 分割
    parts = line.split(' & ')
    for part in parts:
        part = part.strip()
        if part:
            companies.append(part)
    
    return companies


def parse_new_companies_file(content: str) -> Dict[str, List[str]]:
    """
    解析新增企业清单文件
    
    返回: {node_path: [company1, company2, ...]}
    """
    companies_map = defaultdict(list)
    
    # 匹配节点块
    # ### 节点：{路径}
    # **层级**: {X}级
    # **新增企业**: {企业列表}
    
    pattern = r'### 节点：(.+?)\n\*\*层级\*\*:\s*\d+级\n\*\*新增企业\*\*:\s*(.+?)(?=\n### 节点：|\n---|\Z)'
    
    matches = re.findall(pattern, content, re.DOTALL)
    
    for node_path, company_line in matches:
        node_path = node_path.strip()
        company_line = company_line.strip()
        
        if company_line:
            companies = parse_company_line(company_line)
            if companies:
                companies_map[node_path] = companies
    
    return dict(companies_map)


def build_node_path_map(content: str) -> Dict[str, Tuple[int, int]]:
    """
    构建节点路径到行号的映射
    
    返回: {node_path: (level, line_number)}
    """
    path_map = {}
    lines = content.split('\n')
    
    current_path = []
    
    for i, line in enumerate(lines):
        header_match = re.match(r'^(#{1,7})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            node_name = header_match.group(2).strip()
            
            # 更新路径
            if level <= len(current_path):
                current_path = current_path[:level-1]
            current_path.append(node_name)
            
            node_path = ' > '.join(current_path)
            path_map[node_path] = (level, i)
    
    return path_map


def merge_companies(
    original_companies: Dict[str, List[str]],
    new_companies: Dict[str, List[str]],
    skeleton_content: str
) -> str:
    """
    合并企业数据到骨架图谱
    """
    lines = skeleton_content.split('\n')
    result_lines = []
    
    current_path = []
    last_node_level = 0
    last_node_path = ""
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检测标题层级
        header_match = re.match(r'^(#{1,7})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            node_name = header_match.group(2).strip()
            
            # 更新路径
            if level <= len(current_path):
                current_path = current_path[:level-1]
            current_path.append(node_name)
            
            node_path = ' > '.join(current_path)
            last_node_level = level
            last_node_path = node_path
            
            result_lines.append(line)
            
            # 如果是四级及以下节点，检查是否需要添加企业
            if level >= 4:
                # 合并原有企业和新增企业
                all_companies = []
                
                if node_path in original_companies:
                    all_companies.extend(original_companies[node_path])
                
                if node_path in new_companies:
                    all_companies.extend(new_companies[node_path])
                
                # 去重
                all_companies = deduplicate_companies(all_companies)
                
                if all_companies:
                    company_line = format_companies(all_companies)
                    result_lines.append(company_line)
            
        else:
            result_lines.append(line)
        
        i += 1
    
    return '\n'.join(result_lines)


def deduplicate_companies(companies: List[str]) -> List[str]:
    """
    企业去重
    
    按企业简称去重，保留第一次出现的企业
    """
    seen = set()
    result = []
    
    for company in companies:
        # 提取简称
        match = re.match(r'^(.+?)\s*\(', company)
        if match:
            short_name = match.group(1).strip()
        else:
            short_name = company.strip()
        
        if short_name not in seen:
            seen.add(short_name)
            result.append(company)
    
    return result


def format_companies(companies: List[str]) -> str:
    """
    格式化企业列表
    
    输出: **企业1 (企业1全称) & 企业2 (企业2全称)**
    """
    return '**' + ' & '.join(companies) + '**'


def validate_files(args):
    """验证输入文件是否存在"""
    files = {
        '原始图谱': args.original,
        'V2骨架': args.skeleton,
        '新增企业': args.new_companies
    }
    
    for name, path in files.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"{name}文件不存在: {path}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("产业链图谱企业合并脚本")
    print("=" * 60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 验证文件
    print("[1/5] 验证输入文件...")
    validate_files(args)
    print("  ✓ 所有输入文件存在")
    print()
    
    # 读取文件
    print("[2/5] 读取输入文件...")
    with open(args.original, 'r', encoding='utf-8') as f:
        original_content = f.read()
    print(f"  ✓ 原始图谱: {len(original_content)} 字符")
    
    with open(args.skeleton, 'r', encoding='utf-8') as f:
        skeleton_content = f.read()
    print(f"  ✓ V2骨架: {len(skeleton_content)} 字符")
    
    with open(args.new_companies, 'r', encoding='utf-8') as f:
        new_companies_content = f.read()
    print(f"  ✓ 新增企业: {len(new_companies_content)} 字符")
    print()
    
    # 提取企业数据
    print("[3/5] 解析企业数据...")
    original_companies = extract_companies_from_graph(original_content)
    print(f"  ✓ 原有企业节点数: {len(original_companies)}")
    original_total = sum(len(v) for v in original_companies.values())
    print(f"  ✓ 原有企业总数: {original_total}")
    
    new_companies = parse_new_companies_file(new_companies_content)
    print(f"  ✓ 新增企业节点数: {len(new_companies)}")
    new_total = sum(len(v) for v in new_companies.values())
    print(f"  ✓ 新增企业总数: {new_total}")
    print()
    
    # 合并企业
    print("[4/5] 合并企业数据...")
    merged_content = merge_companies(original_companies, new_companies, skeleton_content)
    print(f"  ✓ 合并完成: {len(merged_content)} 字符")
    print()
    
    # 写入输出
    print("[5/5] 写入输出文件...")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(merged_content)
    print(f"  ✓ 输出文件: {args.output}")
    print()
    
    # 统计
    print("=" * 60)
    print("合并统计")
    print("=" * 60)
    print(f"原有企业节点: {len(original_companies)} 个")
    print(f"原有企业总数: {original_total} 家")
    print(f"新增企业节点: {len(new_companies)} 个")
    print(f"新增企业总数: {new_total} 家")
    print(f"输出文件大小: {len(merged_content)} 字符")
    print()
    print("✅ 企业合并完成！")


if __name__ == '__main__':
    main()