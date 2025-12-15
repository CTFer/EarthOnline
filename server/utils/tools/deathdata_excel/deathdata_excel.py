import pandas as pd
import os
from pathlib import Path
import re
import configparser

# 配置文件路径
CONFIG_FILE = "config.ini"

# 默认配置
DEFAULT_CONFIG = {
    "MAIN_EXCEL_PATH": "主表.xlsx",
    "SUB_EXCEL_PATH": "附表.xlsx",
    "OUTPUT_DIR": "./人员数据处理结果"
}

def load_config():
    """加载配置文件，如果不存在则创建默认配置文件"""
    config = configparser.ConfigParser()
    
    # 如果配置文件不存在，创建默认配置文件
    if not os.path.exists(CONFIG_FILE):
        config["DEFAULT"] = DEFAULT_CONFIG
        with open(CONFIG_FILE, "w") as f:
            config.write(f)
        print(f"已创建默认配置文件：{CONFIG_FILE}")
    
    # 读取配置文件
    config.read(CONFIG_FILE)
    
    # 获取配置项，使用默认值作为后备
    main_excel_path = config["DEFAULT"].get("MAIN_EXCEL_PATH", DEFAULT_CONFIG["MAIN_EXCEL_PATH"])
    sub_excel_path = config["DEFAULT"].get("SUB_EXCEL_PATH", DEFAULT_CONFIG["SUB_EXCEL_PATH"])
    output_dir = config["DEFAULT"].get("OUTPUT_DIR", DEFAULT_CONFIG["OUTPUT_DIR"])
    
    return main_excel_path, sub_excel_path, output_dir

def init_dir(output_dir):
    """初始化输出目录，不存在则创建"""
    Path(output_dir).mkdir(exist_ok=True)
    Path(f"{output_dir}/按户籍拆分").mkdir(exist_ok=True)

def check_columns(df, required_cols, file_name):
    """检查DataFrame是否包含必需列，缺失则抛出异常"""
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"{file_name}缺失必需列：{','.join(missing_cols)}")

def validate_id_card(id_card):
    """验证身份证号合法性，18位身份证号校验"""
    if pd.isna(id_card):
        return False
    id_card = str(id_card).strip()
    # 18位身份证号正则
    pattern = r'^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$'
    if not re.match(pattern, id_card):
        return False
    return True

def process_dataframe(df, file_name):
    """处理DataFrame，清理空行和缺失数据"""
    # 移除全部为空的行
    df = df.dropna(how='all').reset_index(drop=True)
    # 移除必需列包含空值的行
    if "户籍所在乡镇（街道）" in df.columns:
        required_cols = ["姓名", "身份证号", "户籍所在乡镇（街道）"]
    else:
        required_cols = ["姓名", "身份证号"]
    
    # 记录并移除必需列有空值的行
    null_rows = df[df[required_cols].isnull().any(axis=1)]
    if not null_rows.empty:
        print(f"{file_name}中移除了{len(null_rows)}行必需列有空值的数据")
    
    df = df.dropna(subset=required_cols).reset_index(drop=True)
    
    # 身份证号合法性校验
    invalid_ids = df[~df["身份证号"].apply(validate_id_card)]
    if not invalid_ids.empty:
        print(f"{file_name}中移除了{len(invalid_ids)}行身份证号无效的数据")
    
    df = df[df["身份证号"].apply(validate_id_card)].reset_index(drop=True)
    return df

def main():
    try:
        # 1. 加载配置
        print("加载配置文件...")
        MAIN_EXCEL_PATH, SUB_EXCEL_PATH, OUTPUT_DIR = load_config()
        print(f"主表路径：{MAIN_EXCEL_PATH}")
        print(f"附表路径：{SUB_EXCEL_PATH}")
        print(f"输出目录：{OUTPUT_DIR}")
        
        # 2. 初始化目录
        init_dir(OUTPUT_DIR)

        # 3. 读取并校验输入文件
        print("读取主表和附表数据...")
        df_main = pd.read_excel(MAIN_EXCEL_PATH, engine="openpyxl")
        df_sub = pd.read_excel(SUB_EXCEL_PATH, engine="openpyxl")
        
        # 显示读取结果
        print(f"主表读取了{len(df_main)}条数据")
        print(f"附表读取了{len(df_sub)}条数据")
        
        # 校验必需列
        check_columns(df_main, ["姓名", "身份证号", "户籍所在乡镇（街道）"], "主表")
        check_columns(df_sub, ["姓名", "身份证号"], "附表")
        
        # 处理数据，清理空行和缺失数据
        print("处理主表数据...")
        df_main_original = len(df_main)
        df_main = process_dataframe(df_main, "主表")
        print(f"主表处理后剩余{len(df_main)}条有效数据")
        
        print("处理附表数据...")
        df_sub_original = len(df_sub)
        df_sub = process_dataframe(df_sub, "附表")
        print(f"附表处理后剩余{len(df_sub)}条有效数据")
        
        # 检查处理后的数据是否为空
        if df_main.empty:
            raise ValueError("主表处理后无有效数据")
        if df_sub.empty:
            raise ValueError("附表处理后无有效数据")

        # 4. 匹配人员并生成表C
        print("匹配主表与附表人员...")
        # 提取附表身份证号列表
        sub_id_list = df_sub["身份证号"].tolist()
        # 筛选主表中身份证号在附表中的数据
        df_c = df_main[df_main["身份证号"].isin(sub_id_list)].copy()
        # 保存表C
        c_path = f"{OUTPUT_DIR}/匹配人员表C.xlsx"
        df_c.to_excel(c_path, index=False, engine="openpyxl")
        print(f"表C已生成：{c_path}，共{len(df_c)}条数据")

        # 5. 生成匹配表-附表对比表
        print("生成匹配表-附表对比表...")
        # 只选择附表的核心字段（姓名、身份证号）
        df_compare = df_sub[["姓名", "身份证号"]].copy()
        # 判断附表人员是否在匹配表C中
        df_compare["匹配表存在状态"] = df_compare["身份证号"].apply(
            lambda x: "匹配表存在" if x in df_c["身份证号"].values else "匹配表不存在"
        )
        # 保存对比表
        compare_path = f"{OUTPUT_DIR}/匹配表-附表对比表.xlsx"
        df_compare.to_excel(compare_path, index=False, engine="openpyxl")
        print(f"对比表已生成：{compare_path}")

        # 6. 按户籍拆分表C
        print("按户籍拆分表C...")
        if not df_c.empty:
            # 按户籍分组
            group_by_hj = df_c.groupby("户籍所在乡镇（街道）")
            for hj_name, group_df in group_by_hj:
                # 处理户籍名称中的特殊字符（避免文件名非法）
                safe_hj_name = hj_name.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")
                split_path = f"{OUTPUT_DIR}/按户籍拆分/{safe_hj_name}.xlsx"
                group_df.to_excel(split_path, index=False, engine="openpyxl")
                print(f"户籍[{hj_name}]的文件已生成：{split_path}，共{len(group_df)}条数据")
        else:
            print("表C为空，无需按户籍拆分")

        print("所有操作执行完成！")

    except FileNotFoundError as e:
        print(f"错误：文件不存在 - {e}")
    except ValueError as e:
        print(f"错误：数据校验失败 - {e}")
    except Exception as e:
        print(f"未知错误：{e}")

if __name__ == "__main__":
    main()
