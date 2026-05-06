#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将对应行业、对应公司的主体关系图谱写入到 MySQL 数据库中。

用法:
    python md_to_mysql.py <行业> <公司名称> <comcode> <图谱markdown文件路径>

示例:
    python md_to_mysql.py 智能驾驶 Waymo 8195554 ./图谱/智能驾驶_Waymo_主体关系图谱.md
"""

import sys
import os
import copy
import json
import time
import logging
from datetime import datetime
from typing import List

import requests
import pandas as pd
import pymysql

# ============================================================
# 配置
# ============================================================
VAR_TIMEOUT = 0.01
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'password',
    'database': 'test_db',
    'charset': 'utf8mb4'
}

NER_URL = "http://168.63.65.40:8090/pai/xapi/at/tjkjV2/enitylabel/label/"
NER_HEADERS = {
    "appSysId": "001038",
    "token": "2303ff18055e4841a52daa54858d7611"
}
NER_BODY = {
    "param": {
        "ner_modules": ["lac", "ner_model", "hanlp"],
        "model_name": "entity_assess",
        "segments": [{"blocks": [{"type": "text", "content": ""}]}]
    }
}

SAMETRACK_INVEST_EXCEL = (
    '/Users/mingyue/Documents/13_GithubAdd/nanobot_main/'
    '.nanobot_root/workspaces/web-scf-test3/图谱/ad_sametrack_invest.xlsx'
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

GRAPH_MD_WITH_COMCODE_COLUMNS = [
    'comcode', 'comname_std', 'relation_type', 'relation_sub_type',
    'relation_comcode', 'relation_comname', 'relation_comfullname',
    'source', 'source_text', 'is_trading_llm',
    '零部件一级分类', '零部件二级分类', '零部件三级分类'
]

GRAPH_MD_COLUMNS = [
    'comname_std', 'relation_type', 'relation_sub_type',
    'relation_comname', 'relation_comfullname',
    'source', 'source_text', 'is_trading_llm',
    '零部件一级分类', '零部件二级分类', '零部件三级分类'
]


# ============================================================
# 数据库工具
# ============================================================

def get_connection():
    return pymysql.connect(**DB_CONFIG)


def query_latest_record(industry: str, company: str):
    """查询 version!='TBD' 的最新记录，返回 (graph_md, graph_md_with_comcode) 或 (None, None)"""
    sql = """
        SELECT graph_md, graph_md_with_comcode
        FROM company_graph
        WHERE industry = %s AND graph_company_name = %s AND version != 'TBD'
        ORDER BY create_datetime DESC LIMIT 1
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (industry, company))
            row = cur.fetchone()
            return (row[0], row[1]) if row else (None, None)
    finally:
        conn.close()


def query_tbd_records(industry: str, company: str) -> List[str]:
    """查询 version='TBD' 的所有记录，返回 graph_md 列表"""
    sql = """
        SELECT graph_md FROM company_graph
        WHERE industry = %s AND graph_company_name = %s AND version = 'TBD'
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (industry, company))
            return [r[0] for r in cur.fetchall() if r[0]]
    finally:
        conn.close()


def insert_graph_record(industry, company, comcode, graph_md, graph_md_with_comcode):
    """插入 company_graph 记录，version='SCRATCH'"""
    now = datetime.now().strftime('%Y%m%d %H:%M:%S')
    sql = """
        INSERT INTO company_graph
            (industry, graph_type, graph_content, graph_company_name,
             graph_company_code, version, create_datetime,
             graph_md, graph_md_with_comcode, graph_json, update_datetime, ext)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (
                industry, '主体关系图谱', '', company, comcode,
                'SCRATCH', now, graph_md, graph_md_with_comcode, '', now, ''
            ))
        conn.commit()
        logger.info("成功插入 company_graph 记录")
    finally:
        conn.close()


# ============================================================
# 实体识别接口
# ============================================================

def call_entity_recognition_api(company_name: str) -> List:
    """调用实体识别接口，返回 [comcode, stock_infos_str, is_trading_company]"""
    try:
        payload = copy.deepcopy(NER_BODY)
        payload['param']["segments"][0]["blocks"][0]["content"] = company_name
        ret = requests.post(NER_URL, headers=NER_HEADERS, json=payload, timeout=VAR_TIMEOUT)
        json_data = ret.json()

        if "content" not in json_data or "entity_assess" not in json_data["content"]:
            logger.warning(f"实体识别返回格式异常: {company_name}")
            return ['', '', '否']

        content = json_data["content"]["entity_assess"]["intermediate"]["extract"]["detail"]["content"]
        if not content:
            logger.info(f"实体识别未找到: {company_name}")
            return ['', '', '否']

        com_code = '0'
        stock_infos = []
        for subject in content[0]["subject"]:
            try:
                if int(com_code) == 0 or len(subject["stock_infos"]) > len(stock_infos):
                    com_code = subject["com_code"]
                    stock_infos = subject["stock_infos"]
                elif int(subject["com_code"]) < int(com_code) and len(subject["stock_infos"]) >= len(stock_infos):
                    com_code = subject["com_code"]
                    stock_infos = subject["stock_infos"]
            except Exception as e:
                logger.warning(f"解析 subject 失败: {e}")
                continue

        stock_infos_str = json.dumps(stock_infos, ensure_ascii=False)
        is_trading = '是' if len(stock_infos_str) > 8 else '否'
        logger.info(f"实体识别成功: {company_name} -> comcode={com_code}")
        return [com_code, stock_infos_str, is_trading]

    except requests.exceptions.Timeout:
        logger.error(f"实体识别超时: {company_name}")
        return ['', '', '否']
    except Exception as e:
        logger.error(f"实体识别失败: {company_name}, {e}")
        return ['', '', '否']


# ============================================================
# Markdown 解析与合并
# ============================================================

def parse_md_table(md_text: str) -> pd.DataFrame:
    """将 markdown 表格解析为 DataFrame，兼容表头瑕疵"""
    if not md_text or not md_text.strip():
        return pd.DataFrame()

    lines = [l for l in md_text.strip().split('\n') if l.strip()]

    header_line = None
    data_start = 0
    for i, line in enumerate(lines):
        if '|' in line:
            stripped = line.replace('|', '').replace('-', '').replace(' ', '').replace(':', '')
            if stripped == '':
                continue
            if header_line is None:
                header_line = line
                data_start = i + 1
                break

    if header_line is None:
        return pd.DataFrame()

    headers = [h.strip() for h in header_line.split('|') if h.strip()]

    rows = []
    for line in lines[data_start:]:
        stripped = line.replace('|', '').replace('-', '').replace(' ', '').replace(':', '')
        if stripped == '' or '|' not in line:
            continue
        cells = [c.strip() for c in line.split('|')]
        cells = cells[1:]
        if len(cells) > len(headers):
            cells = cells[:len(headers)]
        while len(cells) < len(headers):
            cells.append('')
        rows.append(cells)

    return pd.DataFrame(rows, columns=headers) if rows else pd.DataFrame(columns=headers)


def df_to_md_table(df: pd.DataFrame) -> str:
    """DataFrame 转 markdown 表格"""
    if df.empty:
        return ''
    headers = list(df.columns)
    lines = [
        '| ' + ' | '.join(headers) + ' |',
        '| ' + ' | '.join(['----'] * len(headers)) + ' |'
    ]
    for _, row in df.iterrows():
        vals = [str(v) if pd.notna(v) and str(v) != 'nan' else '' for v in row]
        lines.append('| ' + ' | '.join(vals) + ' |')
    return '\n'.join(lines)


def merge_md_tables(md_list: List[str]) -> str:
    """合并多个 markdown 表格，以第一个非空表格的表头为基准，兼容表头瑕疵"""
    dfs = []
    base_columns = None
    for md in md_list:
        if not md or not md.strip():
            continue
        df = parse_md_table(md)
        if df.empty:
            continue
        if base_columns is None:
            base_columns = list(df.columns)
        dfs.append(df)

    if not dfs:
        return ''

    aligned = []
    for df in dfs:
        if list(df.columns) == base_columns:
            aligned.append(df)
        else:
            new_df = pd.DataFrame(columns=base_columns)
            for col in base_columns:
                if col in df.columns:
                    new_df[col] = df[col].values
                else:
                    new_df[col] = ''
            aligned.append(new_df)

    merged = pd.concat(aligned, ignore_index=True).drop_duplicates()
    return df_to_md_table(merged)


def merge_two_dfs(df_orig: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    """将两个 DataFrame 按行合并（纵向拼接），去重后返回。列以 df_new 为基准对齐。"""
    if df_orig is None or df_orig.empty:
        return df_new.copy()
    if df_new is None or df_new.empty:
        return df_orig.copy()

    base_columns = list(df_new.columns)
    aligned_orig = pd.DataFrame(columns=base_columns)
    for col in base_columns:
        if col in df_orig.columns:
            aligned_orig[col] = df_orig[col].values
        else:
            aligned_orig[col] = ''

    merged = pd.concat([aligned_orig, df_new], ignore_index=True).drop_duplicates()
    return merged


# ============================================================
# 核心流程
# ============================================================

def enrich_df_with_comcode(df: pd.DataFrame, comcode: str) -> pd.DataFrame:
    """
    给 DataFrame 增加 comcode 和 relation_comcode 两列。
    - comcode: 直接使用入参
    - relation_comcode: 优先用 relation_comfullname，其次用 relation_comname 调用实体识别接口
    返回按 GRAPH_MD_WITH_COMCODE_COLUMNS 列顺序排列的 DataFrame。
    """
    df = df.copy()
    df['comcode'] = comcode
    df['relation_comcode'] = ''

    total = len(df)
    success = 0

    for idx in df.index:
        fullname = str(df.at[idx, 'relation_comfullname']).strip() if 'relation_comfullname' in df.columns else ''
        abbr = str(df.at[idx, 'relation_comname']).strip() if 'relation_comname' in df.columns else ''

        query_name = fullname if fullname else abbr
        if not query_name:
            continue

        result = call_entity_recognition_api(query_name)
        if result[0]:
            df.at[idx, 'relation_comcode'] = result[0]
            success += 1
        elif fullname and abbr and query_name == fullname:
            result = call_entity_recognition_api(abbr)
            if result[0]:
                df.at[idx, 'relation_comcode'] = result[0]
                success += 1

        if (idx + 1) % 10 == 0:
            time.sleep(0.1)
        if (idx + 1) % 50 == 0:
            logger.info(f"实体识别进度: {idx + 1}/{total}, 成功: {success}")

    logger.info(f"实体识别完成: 成功 {success}/{total}")

    result_df = pd.DataFrame(columns=GRAPH_MD_WITH_COMCODE_COLUMNS)
    for col in GRAPH_MD_WITH_COMCODE_COLUMNS:
        result_df[col] = df[col].values if col in df.columns else ''
    return result_df


def load_sametrack_invest_df(comcode: str, comname_std: str) -> pd.DataFrame:
    """
    读取 ad_sametrack_invest.xlsx，按 comcode 或 comname_std 过滤，
    补齐 is_trading_llm / 零部件一级分类 / 零部件二级分类 / 零部件三级分类 列（默认空字符串），
    返回与 GRAPH_MD_WITH_COMCODE_COLUMNS 对齐的 DataFrame。
    """
    if not os.path.exists(SAMETRACK_INVEST_EXCEL):
        logger.warning(f"Excel 文件不存在: {SAMETRACK_INVEST_EXCEL}")
        return pd.DataFrame()

    try:
        df = pd.read_excel(SAMETRACK_INVEST_EXCEL)
    except Exception as e:
        logger.error(f"读取 Excel 失败: {e}")
        return pd.DataFrame()

    # 去掉可能存在的无名索引列
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]

    # 统一 comcode 列为字符串
    if 'comcode' in df.columns:
        df['comcode'] = df['comcode'].astype(str).str.strip()

    # 按 comcode 或 comname_std 过滤
    mask = pd.Series(False, index=df.index)
    if 'comcode' in df.columns:
        mask = mask | (df['comcode'] == str(comcode).strip())
    if 'comname_std' in df.columns:
        mask = mask | (df['comname_std'] == str(comname_std).strip())
    df = df[mask].copy()

    if df.empty:
        return df

    # 补齐缺失列
    for col in ['is_trading_llm', '零部件一级分类', '零部件二级分类', '零部件三级分类']:
        if col not in df.columns:
            df[col] = ''

    # 按 GRAPH_MD_WITH_COMCODE_COLUMNS 对齐
    aligned = pd.DataFrame(columns=GRAPH_MD_WITH_COMCODE_COLUMNS)
    for col in GRAPH_MD_WITH_COMCODE_COLUMNS:
        if col in df.columns:
            aligned[col] = df[col].values
        else:
            aligned[col] = ''

    aligned = aligned.fillna('')
    logger.info(f"load_sametrack_invest_df: 匹配到 {len(aligned)} 行")
    return aligned


def main():
    if len(sys.argv) < 5:
        # python md_to_mysql.py "智能驾驶" "Waymo" "8195554" "./图谱/智能驾驶_Waymo_主体关系图谱.md"
        print("用法: python md_to_mysql.py <行业> <公司名称> <comcode> <图谱markdown文件路径>")
        print("示例: python md_to_mysql.py 智能驾驶 Waymo 8195554 ./图谱/智能驾驶_Waymo_主体关系图谱.md")
        sys.exit(1)

    industry = sys.argv[1]
    company = sys.argv[2]
    comcode = sys.argv[3]       # 保存为字符串
    md_file_path = sys.argv[4]

    logger.info(f"参数: 行业={industry}, 公司={company}, comcode={comcode}, 文件={md_file_path}")

    # -------------------------------------------------------
    # 步骤1: 查询数据库中最新的非 TBD 记录
    # -------------------------------------------------------
    logger.info("步骤1: 查询最新非 TBD 记录...")
    graph_md_raw, graph_md_with_comcode_raw = query_latest_record(industry, company)

    graph_md_orig = parse_md_table(graph_md_raw) if graph_md_raw else None
    graph_md_with_comcode_orig = parse_md_table(graph_md_with_comcode_raw) if graph_md_with_comcode_raw else None

    if graph_md_orig is not None:
        logger.info(f"  已加载原始 graph_md, 行数: {len(graph_md_orig)}")
    else:
        logger.info("  数据库中无非 TBD 记录")

    if graph_md_with_comcode_orig is not None:
        logger.info(f"  已加载原始 graph_md_with_comcode, 行数: {len(graph_md_with_comcode_orig)}")

    # -------------------------------------------------------
    # 步骤2: 查询所有 TBD 记录
    # -------------------------------------------------------
    logger.info("步骤2: 查询 TBD 记录...")
    lyst_graph_md_tbd = query_tbd_records(industry, company)
    logger.info(f"  TBD 记录数: {len(lyst_graph_md_tbd)}")

    # -------------------------------------------------------
    # 步骤3: 读取本次图谱文件
    # -------------------------------------------------------
    if not os.path.exists(md_file_path):
        logger.error(f"文件不存在: {md_file_path}")
        sys.exit(1)

    with open(md_file_path, 'r', encoding='utf-8') as f:
        graph_md_thistime = f.read()
    logger.info(f"步骤3: 已读取本次图谱文件: {md_file_path}")

    # -------------------------------------------------------
    # 步骤4: 合并 lyst_graph_md_tbd + graph_md_thistime
    # -------------------------------------------------------
    graph_md = merge_md_tables(lyst_graph_md_tbd + [graph_md_thistime])
    logger.info("步骤4: 已合并 TBD + 本次图谱 -> graph_md")

    # -------------------------------------------------------
    # 步骤5: graph_md 转 DataFrame
    # -------------------------------------------------------
    graph_md_df = parse_md_table(graph_md)
    logger.info(f"步骤5: graph_md_df 行数: {len(graph_md_df)}")

    if graph_md_df.empty:
        logger.error("合并后 DataFrame 为空，退出")
        sys.exit(1)

    # -------------------------------------------------------
    # 步骤6: graph_md_orig 与 graph_md_df 按行合并 -> graph_md_merged
    # -------------------------------------------------------
    graph_md_merged_df = merge_two_dfs(graph_md_orig, graph_md_df)
    graph_md_merged = df_to_md_table(graph_md_merged_df)
    logger.info(f"步骤6: graph_md_merged 行数: {len(graph_md_merged_df)}")

    # -------------------------------------------------------
    # 步骤7: 给 graph_md_df 补充 comcode / relation_comcode
    # -------------------------------------------------------
    logger.info("步骤7: 调用实体识别接口补充 relation_comcode...")
    graph_md_df_enriched = enrich_df_with_comcode(graph_md_df, comcode)

    graph_md_with_comcode = df_to_md_table(graph_md_df_enriched)

    # -------------------------------------------------------
    # 步骤8: graph_md_with_comcode_orig 与 graph_md_with_comcode 按行合并
    # -------------------------------------------------------
    graph_md_with_comcode_new_df = parse_md_table(graph_md_with_comcode)
    graph_md_with_comcode_merged_df = merge_two_dfs(graph_md_with_comcode_orig, graph_md_with_comcode_new_df)
    graph_md_with_comcode_merged = df_to_md_table(graph_md_with_comcode_merged_df)
    logger.info(f"步骤8: graph_md_with_comcode_merged 行数: {len(graph_md_with_comcode_merged_df)}")

    # -------------------------------------------------------
    # 步骤8.5: 加载同赛道/投资 Excel 数据并合并到 graph_md_with_comcode_merged
    # -------------------------------------------------------
    df_sametrack_invest = load_sametrack_invest_df(comcode, company)
    if not df_sametrack_invest.empty:
        graph_md_with_comcode_merged_df = merge_two_dfs(graph_md_with_comcode_merged_df, df_sametrack_invest)
        graph_md_with_comcode_merged = df_to_md_table(graph_md_with_comcode_merged_df)
        logger.info(f"步骤8.5: 合并 sametrack_invest 后行数: {len(graph_md_with_comcode_merged_df)}")
    else:
        logger.info("步骤8.5: sametrack_invest 无匹配数据，跳过")

    # -------------------------------------------------------
    # 步骤9: 插入数据库
    # -------------------------------------------------------
    logger.info("步骤9: 插入数据库...")
    insert_graph_record(industry, company, comcode, graph_md_merged, graph_md_with_comcode_merged)
    logger.info("全部完成")


if __name__ == '__main__':
    main()
