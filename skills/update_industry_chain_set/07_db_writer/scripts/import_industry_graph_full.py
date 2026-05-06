#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
产业链图谱导入脚本
功能：从 Markdown 文件读取产业链图谱，生成节点编码，关联公司信息，并保存到数据库
"""

import pymysql
import json
import re
import sys
import logging
import copy
import time
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import pandas as pd

# # 数据库连接配置
# DB_CONFIG = {
#     'host': 'localhost',
#     'port': 3306,
#     'user': 'root',
#     'password': 'password',
#     'database': 'test_db',
#     'charset': 'utf8mb4'
# }

DB_CONFIG = {
    'host': '168.64.21.39',
    'port': 8880,
    'user': 'hiagent',
    'password': 'ePPYbo458We3_',
    'database': 'aicp'
}

# 实体识别接口配置
NER_URL = "http://168.63.65.40:8090/pai/xapi/at/tjkjV2/enitylabel/label/"
NER_HEADERS = {
    "appSysId": "001038",
    "token": "8f2752d4d31748e5b13102a0402db896"
}
NER_BODY = {
    "param": {
        "ner_modules": ["lac", "ner_model", "hanlp"],
        "model_name": "entity_assess",
        "segments": [{
            "blocks": [{
                "type": "text",
                "content": "华泰证券今天的股价是什么？"
            }]
        }]
    }
}


class IndustryGraphImporter:
    """产业链图谱导入器"""
    
    def __init__(self, industry: str, md_path: str):
        """
        初始化导入器
        
        Args:
            industry: 行业名称
            md_path: Markdown 文件路径
        """
        self.industry = industry
        self.md_path = md_path
        self.connection = None
        
        # 设置日志
        log_filename = f"{industry}_产业链图谱日志_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 数据存储
        self.graph_content_old = None
        self.graph_name = None
        self.graph_node_code = None
        self.version = None
        self.graph_content = None
        self.graph_node_code_update = None
        self.graph_json = None
        
    def connect_db(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(**DB_CONFIG)
            self.logger.info("数据库连接成功")
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            raise
    
    def close_db(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("数据库连接已关闭")
    
    def load_existing_graph(self):
        """从数据库加载已有图谱信息"""
        self.logger.info(f"开始加载行业 '{self.industry}' 的已有图谱信息")
        
        try:
            with self.connection.cursor() as cursor:
                sql = """
                SELECT graph_content, graph_name, graph_node_code, version, create_datetime
                FROM industry_graph
                WHERE graph_name = %s AND version != 'TBD'
                ORDER BY create_datetime DESC
                LIMIT 1
                """
                cursor.execute(sql, (self.industry,))
                result = cursor.fetchone()
                
                if result:
                    self.graph_content_old = result[0]
                    self.graph_name = result[1]
                    node_code_str = result[2]
                    self.version = result[3]
                    
                    # 解析 graph_node_code
                    self.graph_node_code = self._parse_node_code_table(node_code_str)
                    self.logger.info(f"成功加载已有图谱，版本: {self.version}, 节点数: {len(self.graph_node_code)}")
                else:
                    self.logger.warning(f"未找到行业 '{self.industry}' 的已有图谱，将创建新图谱")
                    self.graph_node_code = pd.DataFrame(columns=['node_level', 'node_name', 'node_code'])
                    
        except Exception as e:
            self.logger.error(f"加载已有图谱失败: {e}")
            raise
    
    def _parse_node_code_table(self, node_code_str: str) -> pd.DataFrame:
        """解析节点编码表格字符串"""
        lines = [line.strip() for line in node_code_str.strip().split('\n') if line.strip()]
        
        data = []
        for line in lines:
            if '|' in line and not line.startswith('|:'):
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) == 3 and parts[0] != 'node_level':
                    data.append(parts)
        
        df = pd.DataFrame(data, columns=['node_level', 'node_name', 'node_code'])
        return df

    def load_new_graph_md(self):
        """加载新版图谱 Markdown 文件"""
        self.logger.info(f"开始加载新版图谱文件: {self.md_path}")
        
        try:
            with open(self.md_path, 'r', encoding='utf-8') as f:
                self.graph_content = f.read()
            self.logger.info(f"成功加载新版图谱，内容长度: {len(self.graph_content)}")
        except Exception as e:
            self.logger.error(f"加载新版图谱文件失败: {e}")
            raise
    
    def parse_md_structure(self) -> List[Dict]:
        """解析 Markdown 结构，提取所有节点"""
        self.logger.info("开始解析 Markdown 结构")
        
        nodes = []
        lines = self.graph_content.split('\n')
        
        for i, line in enumerate(lines):
            # 匹配标题行
            match = re.match(r'^(#{1,7})\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                node_name = match.group(2).strip()
                
                # 跳过第一级标题（通常是 "# {行业}产业链图谱"）
                if level == 1:
                    continue
                
                # 实际层级从 1 开始
                actual_level = level - 1
                
                nodes.append({
                    'level': actual_level,
                    'name': node_name,
                    'line_number': i
                })
        
        self.logger.info(f"解析完成，共提取 {len(nodes)} 个节点")
        return nodes
    
    def generate_node_codes(self, nodes: List[Dict]):
        """为新增节点生成编码"""
        self.logger.info("开始为新增节点生成编码")
        
        # 复制已有节点编码
        self.graph_node_code_update = self.graph_node_code.copy()
        
        # 构建已有节点名称到编码的映射
        existing_nodes = set(self.graph_node_code['node_name'].values)
        
        # 行业前缀（从已有编码中提取，或默认使用前两个字符）
        if len(self.graph_node_code) > 0:
            prefix = self.graph_node_code.iloc[0]['node_code'][:2]
        else:
            # 如果没有已有编码，根据行业名称生成前缀
            prefix = self._generate_industry_prefix(self.industry)
        
        # 添加根节点（如果不存在）
        root_code = f"{prefix}000000000000000"
        if f"{self.industry}产业链" not in existing_nodes:
            new_row = pd.DataFrame([{
                'node_level': '0级节点',
                'node_name': f"{self.industry}产业链",
                'node_code': root_code
            }])
            self.graph_node_code_update = pd.concat([self.graph_node_code_update, new_row], ignore_index=True)
            existing_nodes.add(f"{self.industry}产业链")
            self.logger.info(f"添加根节点: {self.industry}产业链 -> {root_code}")
        
        # 记录父节点栈
        parent_stack = [{'level': 0, 'name': f"{self.industry}产业链", 'code': root_code}]
        
        new_nodes_count = 0
        
        for node in nodes:
            node_name = node['name']
            level = node['level']
            
            # 更新父节点栈
            while parent_stack and parent_stack[-1]['level'] >= level:
                parent_stack.pop()
            
            # 检查是否为新增节点
            if node_name not in existing_nodes:
                # 获取父节点
                parent = parent_stack[-1] if parent_stack else None
                
                if parent:
                    # 生成新编码
                    new_code = self._generate_next_code(parent['code'], level, prefix)
                    
                    # 添加到更新列表
                    new_row = pd.DataFrame([{
                        'node_level': f'{level}级节点',
                        'node_name': node_name,
                        'node_code': new_code
                    }])
                    self.graph_node_code_update = pd.concat([self.graph_node_code_update, new_row], ignore_index=True)
                    existing_nodes.add(node_name)
                    new_nodes_count += 1
                    
                    self.logger.info(f"新增节点: {node_name} (Level {level}) -> {new_code}")
                    
                    # 将当前节点加入父节点栈
                    parent_stack.append({'level': level, 'name': node_name, 'code': new_code})
                else:
                    self.logger.warning(f"节点 '{node_name}' 没有找到父节点")
            else:
                # 已存在的节点，获取其编码
                existing_code = self.graph_node_code_update[
                    self.graph_node_code_update['node_name'] == node_name
                ]['node_code'].values[0]
                parent_stack.append({'level': level, 'name': node_name, 'code': existing_code})
        
        self.logger.info(f"节点编码生成完成，新增 {new_nodes_count} 个节点")
    
    def _generate_industry_prefix(self, industry: str) -> str:
        """根据行业名称生成前缀"""
        # 简单映射，可根据需要扩展
        prefix_map = {
            '智能驾驶': 'AD',
            '新能源汽车': 'NE',
            '创新药': 'IP',
            '半导体': 'SC'
        }
        return prefix_map.get(industry, 'XX')
    
    def _generate_next_code(self, parent_code: str, level: int, prefix: str) -> str:
        """生成下一个节点编码"""
        # 获取同级别的所有节点
        level_str = f'{level}级节点'
        same_level_nodes = self.graph_node_code_update[
            self.graph_node_code_update['node_level'] == level_str
        ]
        
        # 筛选出同一父节点下的节点
        parent_prefix = self._get_parent_prefix(parent_code, level)
        sibling_codes = []
        
        for code in same_level_nodes['node_code'].values:
            if code.startswith(parent_prefix):
                sibling_codes.append(code)
        
        # 找到最大编号
        if sibling_codes:
            max_num = 0
            for code in sibling_codes:
                num = self._extract_level_number(code, level)
                if num > max_num:
                    max_num = num
            next_num = max_num + 1
        else:
            next_num = 1
        
        # 生成新编码
        new_code = self._build_code(parent_code, level, next_num, prefix)
        return new_code
    
    def _get_parent_prefix(self, parent_code: str, child_level: int) -> str:
        """获取父节点前缀，用于匹配同级节点"""
        if child_level <= 3:
            # 前三级，每级占2位
            end_pos = 2 + child_level * 2
        else:
            # 后三级，前三级占6位，后面每级占3位
            end_pos = 2 + 6 + (child_level - 3) * 3
        
        return parent_code[:end_pos]
    
    def _extract_level_number(self, code: str, level: int) -> int:
        """从编码中提取指定层级的编号"""
        if level <= 3:
            start_pos = 2 + (level - 1) * 2
            end_pos = start_pos + 2
        else:
            start_pos = 2 + 6 + (level - 4) * 3
            end_pos = start_pos + 3
        
        try:
            return int(code[start_pos:end_pos])
        except:
            return 0
    
    def _build_code(self, parent_code: str, level: int, number: int, prefix: str) -> str:
        """构建新的节点编码"""
        # 从父编码开始
        code_list = list(parent_code)
        
        # 确定当前层级的位置和宽度
        if level <= 3:
            start_pos = 2 + (level - 1) * 2
            width = 2
        else:
            start_pos = 2 + 6 + (level - 4) * 3
            width = 3
        
        # 填充编号
        num_str = str(number).zfill(width)
        for i, char in enumerate(num_str):
            code_list[start_pos + i] = char
        
        return ''.join(code_list)

    def load_company_info(self) -> Tuple[Dict, Dict]:
        """从数据库加载公司信息"""
        self.logger.info("开始加载公司信息")
        
        d_abbr_exists = {}
        d_fullname_exists = {}
        
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT comabbr, comfullname, comcode, stock_info, is_trading_company FROM comcode"
                cursor.execute(sql)
                results = cursor.fetchall()
                
                for row in results:
                    comabbr = row[0]
                    comfullname = row[1]
                    comcode = row[2] if row[2] else ''
                    stock_info = row[3] if row[3] else ''
                    is_trading = row[4] if row[4] else '否'
                    
                    if comabbr:
                        d_abbr_exists[comabbr] = [comcode, stock_info, is_trading]
                    if comfullname:
                        d_fullname_exists[comfullname] = [comcode, stock_info, is_trading]
                
                self.logger.info(f"成功加载公司信息，简称: {len(d_abbr_exists)}, 全称: {len(d_fullname_exists)}")
                
        except Exception as e:
            self.logger.error(f"加载公司信息失败: {e}")
            raise
        
        return d_abbr_exists, d_fullname_exists
    
    def extract_companies_from_md(self) -> Tuple[Dict, Dict]:
        """从 Markdown 中提取公司信息"""
        self.logger.info("开始从 Markdown 中提取公司信息")
        
        d_abbr = {}
        d_fullname = {}
        
        # 匹配公司信息的正则表达式：**企业简称(企业全称)&企业简称(企业全称)**
        pattern = r'\*\*(.+?)\*\*'
        
        matches = re.findall(pattern, self.graph_content)
        
        for match in matches:
            # 按 & 分割多个公司
            companies = match.split('&')
            
            for company in companies:
                company = company.strip()
                # 匹配 "简称(全称)" 格式
                company_match = re.match(r'(.+?)\((.+?)\)', company)
                
                if company_match:
                    abbr = company_match.group(1).strip()
                    fullname = company_match.group(2).strip()
                    
                    if abbr and abbr not in d_abbr:
                        d_abbr[abbr] = ['', '', '否']
                    if fullname and fullname not in d_fullname:
                        d_fullname[fullname] = ['', '', '否']
        
        self.logger.info(f"从 Markdown 提取公司，简称: {len(d_abbr)}, 全称: {len(d_fullname)}")
        return d_abbr, d_fullname
    
    def call_entity_recognition_api(self, company_name: str) -> List:
        """
        调用实体识别接口获取公司信息
        
        Args:
            company_name: 公司名称（简称或全称）
            
        Returns:
            [comcode, stock_infos, is_trading_company] 或 ['', '', '否']
        """
        try:
            payload = copy.deepcopy(NER_BODY)
            payload['param']["segments"][0]["blocks"][0]["content"] = company_name
            
            ret = requests.post(NER_URL, headers=NER_HEADERS, json=payload, timeout=30)
            json_data = ret.json()
            
            # 检查返回数据
            if "content" not in json_data or "entity_assess" not in json_data["content"]:
                self.logger.warning(f"实体识别接口返回数据格式异常: {company_name}")
                return ['', '', '否']
            
            content = json_data["content"]["entity_assess"]["intermediate"]["extract"]["detail"]["content"]
            
            if len(content) <= 0:
                self.logger.info(f"实体识别接口未找到公司信息: {company_name}")
                return ['', '', '否']
            
            # 解析返回结果
            com_code = '0'
            default_value = ''
            norm_name = ''
            stock_infos = []
            
            item = content[0]
            for subject in item["subject"]:
                try:
                    # 选择最优的 comcode（优先选择有股票信息的，其次选择编号小的）
                    if int(com_code) == 0 or len(subject["stock_infos"]) > len(stock_infos):
                        com_code = subject["com_code"]
                        default_value = subject["default_value"]
                        norm_name = subject["norm_name"]
                        stock_infos = subject["stock_infos"]
                    elif int(subject["com_code"]) < int(com_code) and len(subject["stock_infos"]) >= len(stock_infos):
                        com_code = subject["com_code"]
                        default_value = subject["default_value"]
                        norm_name = subject["norm_name"]
                        stock_infos = subject["stock_infos"]
                except Exception as e:
                    self.logger.warning(f"解析 subject 数据失败: {e}")
                    continue
            
            # 转换 stock_infos 为 JSON 字符串
            stock_infos_str = json.dumps(stock_infos, ensure_ascii=False)
            
            # 判断是否上市
            is_trading_company = '是' if len(stock_infos_str) > 8 else '否'
            
            self.logger.info(f"实体识别成功: {company_name} -> comcode={com_code}, is_trading={is_trading_company}")
            
            return [com_code, stock_infos_str, is_trading_company]
            
        except requests.exceptions.Timeout:
            self.logger.error(f"实体识别接口超时: {company_name}")
            return ['', '', '否']
        except Exception as e:
            self.logger.error(f"调用实体识别接口失败: {company_name}, 错误: {e}")
            return ['', '', '否']
    
    def enrich_company_info_with_ner(self, d_abbr: Dict, d_fullname: Dict) -> Tuple[Dict, Dict]:
        """
        使用实体识别接口补充缺失的公司信息
        
        Args:
            d_abbr: 公司简称字典
            d_fullname: 公司全称字典
            
        Returns:
            更新后的 (d_abbr, d_fullname)
        """
        self.logger.info("开始使用实体识别接口补充公司信息")
        
        # 找出 comcode 为空的公司简称
        missing_abbr = [abbr for abbr, info in d_abbr.items() if not info[0]]
        self.logger.info(f"需要补充信息的公司简称数量: {len(missing_abbr)}")
        
        # 找出 comcode 为空的公司全称
        missing_fullname = [fullname for fullname, info in d_fullname.items() if not info[0]]
        self.logger.info(f"需要补充信息的公司全称数量: {len(missing_fullname)}")
        
        # 处理公司简称
        abbr_success = 0
        for index, abbr in enumerate(missing_abbr, 1):
            if index % 100 == 0:
                self.logger.info(f"处理进度 (简称): {index}/{len(missing_abbr)}")
            
            # 调用实体识别接口
            result = self.call_entity_recognition_api(abbr)
            
            # 更新字典
            if result[0]:  # 如果获取到了 comcode
                d_abbr[abbr] = result
                abbr_success += 1
            
            # 避免请求过快，适当延迟
            if index % 10 == 0:
                time.sleep(0.1)
        
        self.logger.info(f"公司简称补充完成: 成功 {abbr_success}/{len(missing_abbr)}")
        
        # 处理公司全称
        fullname_success = 0
        for index, fullname in enumerate(missing_fullname, 1):
            if index % 100 == 0:
                self.logger.info(f"处理进度 (全称): {index}/{len(missing_fullname)}")
            
            # 调用实体识别接口
            result = self.call_entity_recognition_api(fullname)
            
            # 更新字典
            if result[0]:  # 如果获取到了 comcode
                d_fullname[fullname] = result
                fullname_success += 1
            
            # 避免请求过快，适当延迟
            if index % 10 == 0:
                time.sleep(0.1)
        
        self.logger.info(f"公司全称补充完成: 成功 {fullname_success}/{len(missing_fullname)}")
        
        # 交叉更新：用全称的结果更新简称，用简称的结果更新全称
        self.logger.info("开始交叉更新公司信息")
        cross_update_count = 0
        
        # 从 Markdown 中提取简称和全称的对应关系
        pattern = r'\*\*(.+?)\*\*'
        matches = re.findall(pattern, self.graph_content)
        
        for match in matches:
            companies = match.split('&')
            for company in companies:
                company = company.strip()
                company_match = re.match(r'(.+?)\((.+?)\)', company)
                
                if company_match:
                    abbr = company_match.group(1).strip()
                    fullname = company_match.group(2).strip()
                    
                    # 如果简称有信息但全称没有，用简称更新全称
                    if abbr in d_abbr and fullname in d_fullname:
                        if d_abbr[abbr][0] and not d_fullname[fullname][0]:
                            d_fullname[fullname] = d_abbr[abbr]
                            cross_update_count += 1
                        # 如果全称有信息但简称没有，用全称更新简称
                        elif d_fullname[fullname][0] and not d_abbr[abbr][0]:
                            d_abbr[abbr] = d_fullname[fullname]
                            cross_update_count += 1
        
        self.logger.info(f"交叉更新完成，更新了 {cross_update_count} 条记录")
        
        return d_abbr, d_fullname
    
    def merge_company_info(self):
        """合并公司信息（增强版：包含实体识别接口调用）"""
        self.logger.info("开始合并公司信息")
        
        # 加载已有公司信息
        d_abbr_exists, d_fullname_exists = self.load_company_info()
        
        # 提取新图谱中的公司
        d_abbr, d_fullname = self.extract_companies_from_md()
        
        # 第一步：用数据库中的已有信息更新
        updated_abbr = 0
        for abbr in d_abbr:
            if abbr in d_abbr_exists:
                d_abbr[abbr] = d_abbr_exists[abbr]
                updated_abbr += 1
        
        updated_fullname = 0
        for fullname in d_fullname:
            if fullname in d_fullname_exists:
                d_fullname[fullname] = d_fullname_exists[fullname]
                updated_fullname += 1
        
        self.logger.info(f"数据库信息合并完成，简称匹配: {updated_abbr}/{len(d_abbr)}, "
                        f"全称匹配: {updated_fullname}/{len(d_fullname)}")
        
        # 第二步：使用实体识别接口补充缺失的信息
        d_abbr, d_fullname = self.enrich_company_info_with_ner(d_abbr, d_fullname)
        
        # 统计最终结果
        abbr_with_code = sum(1 for info in d_abbr.values() if info[0])
        fullname_with_code = sum(1 for info in d_fullname.values() if info[0])
        
        self.logger.info(f"公司信息合并最终结果:")
        self.logger.info(f"  简称: {abbr_with_code}/{len(d_abbr)} 有 comcode")
        self.logger.info(f"  全称: {fullname_with_code}/{len(d_fullname)} 有 comcode")
        
        return d_abbr, d_fullname
    
    def generate_json_graph(self, d_abbr: Dict, d_fullname: Dict):
        """生成 JSON 格式的图谱"""
        self.logger.info("开始生成 JSON 格式图谱")
        
        # 解析 Markdown 结构
        lines = self.graph_content.split('\n')
        
        # 构建节点树
        root = {
            'name': f'{self.industry}产业链',
            'node_code': self._get_node_code(f'{self.industry}产业链'),
            'level': 0,
            'children': [],
            'company': []
        }
        
        # 节点栈，用于构建树形结构
        stack = [root]
        current_node = root
        
        for i, line in enumerate(lines):
            # 匹配标题行
            title_match = re.match(r'^(#{1,7})\s+(.+)$', line)
            
            if title_match:
                level = len(title_match.group(1))
                node_name = title_match.group(2).strip()
                
                # 跳过第一级标题
                if level == 1:
                    continue
                
                actual_level = level - 1
                
                # 创建新节点
                new_node = {
                    'name': node_name,
                    'node_code': self._get_node_code(node_name),
                    'level': actual_level,
                    'children': [],
                    'company': []
                }
                
                # 调整栈，找到父节点
                while len(stack) > actual_level:
                    stack.pop()
                
                # 添加到父节点
                if stack:
                    stack[-1]['children'].append(new_node)
                
                # 当前节点入栈
                stack.append(new_node)
                current_node = new_node
                
            # 匹配公司信息行
            company_match = re.match(r'^\*\*(.+?)\*\*', line)
            if company_match and stack:
                companies_str = company_match.group(1)
                companies = companies_str.split('&')
                
                for company in companies:
                    company = company.strip()
                    company_info_match = re.match(r'(.+?)\((.+?)\)', company)
                    
                    if company_info_match:
                        abbr = company_info_match.group(1).strip()
                        fullname = company_info_match.group(2).strip()
                        
                        # 优先使用简称匹配，其次全称
                        comcode = ''
                        stock_info = ''
                        is_trading = '否'
                        
                        if abbr in d_abbr:
                            comcode, stock_info, is_trading = d_abbr[abbr]
                        elif fullname in d_fullname:
                            comcode, stock_info, is_trading = d_fullname[fullname]
                        
                        company_obj = {
                            'name': abbr,
                            'fullname': fullname,
                            'comcode': comcode,
                            'stock_info': stock_info,
                            'type': is_trading
                        }
                        
                        # 添加到当前节点
                        stack[-1]['company'].append(company_obj)
        
        self.graph_json = json.dumps([root], ensure_ascii=False, indent=2)
        self.logger.info("JSON 格式图谱生成完成")
    
    def _get_node_code(self, node_name: str) -> str:
        """获取节点编码"""
        result = self.graph_node_code_update[
            self.graph_node_code_update['node_name'] == node_name
        ]
        
        if len(result) > 0:
            return result.iloc[0]['node_code']
        else:
            self.logger.warning(f"未找到节点 '{node_name}' 的编码")
            return ''

    def save_to_database(self):
        """保存到数据库"""
        self.logger.info("开始保存到数据库")
        
        try:
            # 生成时间戳
            now = datetime.now().strftime('%Y%m%d %H:%M:%S')
            
            # 将 graph_node_code_update 转换为表格字符串
            node_code_str = self._dataframe_to_table_string(self.graph_node_code_update)
            
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO industry_graph 
                (graph_content, graph_name, version, create_datetime, graph_json, 
                 graph_node_code, graph_md, update_datetime)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql, (
                    self.graph_content,
                    self.industry,
                    'TBD',
                    now,
                    self.graph_json,
                    node_code_str,
                    self.graph_content,  # graph_md 也保存原始内容
                    now
                ))
                
                self.connection.commit()
                self.logger.info(f"成功保存到数据库，行业: {self.industry}, 时间: {now}")
                
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"保存到数据库失败: {e}")
            raise
    
    def _dataframe_to_table_string(self, df: pd.DataFrame) -> str:
        """将 DataFrame 转换为表格字符串"""
        lines = []
        
        # 表头
        lines.append('| node_level | node_name | node_code |')
        lines.append('| :--- | :--- | :--- |')
        
        # 数据行
        for _, row in df.iterrows():
            lines.append(f"| {row['node_level']} | {row['node_name']} | {row['node_code']} |")
        
        return '\n'.join(lines)
    
    def run(self):
        """执行完整流程"""
        try:
            self.logger.info("=" * 80)
            self.logger.info(f"开始执行产业链图谱导入流程")
            self.logger.info(f"行业: {self.industry}")
            self.logger.info(f"文件: {self.md_path}")
            self.logger.info("=" * 80)
            
            # 1. 连接数据库
            self.connect_db()
            
            # 2. 加载已有图谱信息
            self.load_existing_graph()
            
            # 3. 加载新版图谱 Markdown
            self.load_new_graph_md()
            
            # 4. 解析 Markdown 结构
            nodes = self.parse_md_structure()
            
            # 5. 生成节点编码
            self.generate_node_codes(nodes)
            
            # 6. 合并公司信息
            d_abbr, d_fullname = self.merge_company_info()
            
            # 7. 生成 JSON 格式图谱
            self.generate_json_graph(d_abbr, d_fullname)
            print('\n\ngraph_json is {}\n\n'.format(self.graph_json))
            
            # 8. 保存到数据库
            self.save_to_database()
            
            self.logger.info("=" * 80)
            self.logger.info("产业链图谱导入流程执行成功！")
            self.logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            self.logger.error(f"执行过程中发生错误: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
        finally:
            # 关闭数据库连接
            self.close_db()


def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("使用方法: python import_industry_graph.py <行业> <图谱md路径>")
        print("示例: python import_industry_graph_full.py 智能驾驶 ./图谱/智能驾驶_产业链图谱.md")
        sys.exit(1)
    
    industry = sys.argv[1]
    md_path = sys.argv[2]
    
    # 创建导入器并执行
    importer = IndustryGraphImporter(industry, md_path)
    success = importer.run()
    
    if success:
        print(f"\n✓ 成功导入 {industry} 产业链图谱")
        sys.exit(0)
    else:
        print(f"\n✗ 导入 {industry} 产业链图谱失败，请查看日志文件")
        sys.exit(1)


if __name__ == '__main__':
    main()
