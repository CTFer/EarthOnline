import pandas as pd
import sqlite3
import os
from datetime import datetime
import re
import glob

class ExcelToSQLite:
    @staticmethod
    def find_excel_files(directory):
        """
        自动搜索目录下所有Excel文件
        :param directory: 要搜索的目录路径
        :return: Excel文件路径列表
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录不存在：{directory}")
        
        # 搜索.xlsx和.xls文件
        excel_files = []
        excel_files.extend(glob.glob(os.path.join(directory, "*.xlsx")))
        excel_files.extend(glob.glob(os.path.join(directory, "*.xls")))
        
        return sorted(excel_files)
    
    @classmethod
    def batch_convert_directory(cls, directory, output_db=None):
        """
        批量转换目录下所有Excel文件到SQLite
        :param directory: Excel文件所在目录
        :param output_db: 输出的SQLite数据库文件路径（可选，默认在目录下创建combined.db）
        """
        excel_files = cls.find_excel_files(directory)
        
        if not excel_files:
            print(f"⚠️  目录 {directory} 下未找到Excel文件")
            return
        
        print(f"✅ 找到 {len(excel_files)} 个Excel文件")
        
        # 如果指定了输出数据库，所有表都会创建在同一个数据库中
        if output_db:
            for i, excel_file in enumerate(excel_files, 1):
                print(f"\n=== 处理文件 {i}/{len(excel_files)}: {os.path.basename(excel_file)} ===")
                # 使用文件名（不含扩展名）作为表名
                table_name = os.path.splitext(os.path.basename(excel_file))[0]
                try:
                    converter = cls(excel_file, output_db, table_name)
                    converter.export()
                except Exception as e:
                    print(f"❌ 处理文件失败 {excel_file}: {str(e)}")
        else:
            # 否则每个Excel文件创建独立的数据库
            for i, excel_file in enumerate(excel_files, 1):
                print(f"\n=== 处理文件 {i}/{len(excel_files)}: {os.path.basename(excel_file)} ===")
                try:
                    converter = cls(excel_file)
                    converter.export()
                except Exception as e:
                    print(f"❌ 处理文件失败 {excel_file}: {str(e)}")
    
    def __init__(self, excel_path, sqlite_path=None, sheet_name=0, table_name=None, has_header=False):
        """
        初始化配置
        :param excel_path: Excel文件路径（必填）
        :param sqlite_path: SQLite数据库文件路径（默认：与Excel同目录同名.db）
        :param table_name: 数据表名（默认：Excel的sheet名）
        :param sheet_name: 读取Excel的sheet（默认0：第一个sheet，可传sheet名）
        :param has_header: 是否有表头（默认True，设置为False自动生成表头）
        """
        # 验证Excel文件是否存在
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel文件不存在：{excel_path}")
        
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        self.has_header = has_header
        
        # 配置SQLite路径（默认与Excel同目录，同名.db）
        self.sqlite_path = sqlite_path or os.path.splitext(excel_path)[0] + ".db"
        
        # 日志存储
        self.logs = []
        
        # 读取Excel数据
        self.df = self._read_excel()
        
        # 配置表名
        if table_name:
            self.table_name = table_name
        else:
            # 从Excel文件名生成表名
            base_name = os.path.basename(self.excel_path)
            self.table_name = os.path.splitext(base_name)[0].replace(' ', '_')
            self.logs.append(f"📋 自动从文件名生成表名: {self.table_name}")
        
        # 清洗列名（去除特殊字符、空格，避免SQL语法错误）
        self.df.columns = self._clean_column_names(self.df.columns)

    def _read_excel(self):
        """读取Excel文件，返回DataFrame"""
        try:
            # 自动识别Excel格式（.xlsx/.xls）
            # 根据pandas版本调整参数
            read_excel_kwargs = {
                'sheet_name': self.sheet_name,
                'engine': None,  # pandas自动选择引擎（openpyxl/xlrd）
                'header': 0 if self.has_header else None  # 根据has_header参数决定是否使用第一行作为表头
            }
            
            # 尝试使用keep_default_dtype参数（较新版本pandas支持）
            try:
                df = pd.read_excel(self.excel_path, **read_excel_kwargs, keep_default_dtype=False)
            except TypeError:
                # 对于不支持该参数的pandas版本，移除这个参数
                self.logs.append("⚠️ 当前pandas版本不支持keep_default_dtype参数，使用默认数据类型处理")
                df = pd.read_excel(self.excel_path, **read_excel_kwargs)
            
            self.logs.append(f"✅ 成功读取Excel文件：{self.excel_path}")
            # 使用指定的sheet_name而不是df.name，因为df.name在某些pandas版本中不可靠
            sheet_display = self.sheet_name if isinstance(self.sheet_name, str) else f"第{self.sheet_name+1}个" if isinstance(self.sheet_name, int) else "未知"
            self.logs.append(f"📊 读取sheet：{sheet_display}，数据行数：{len(df)}，列数：{len(df.columns)}")
            
            # 如果没有表头，尝试根据数据内容推断并生成表头
            if not self.has_header:
                self.logs.append("ℹ️  检测到无表头Excel文件，正在生成表头...")
                # 先生成临时列名
                temp_columns = [f"column_{i+1}" for i in range(len(df.columns))]
                df.columns = temp_columns
                
                # 尝试根据前几行数据推断列的性质并生成更有意义的列名
                inferred_columns = self._infer_column_names(df)
                self.logs.append(f"✅ 自动生成表头：{inferred_columns}")
                df.columns = inferred_columns
            
            return df
        except Exception as e:
            raise RuntimeError(f"读取Excel失败：{str(e)}")
    
    def _infer_column_names(self, df):
        """
        智能推断列名，根据数据内容识别姓名、电话等信息
        :param df: 无表头的DataFrame
        :return: 推断后的列名列表
        """
        import re
        from collections import Counter
        
        new_columns = []
        # 已使用的列名，避免重复
        used_names = set()
        
        # 用于识别电话的正则表达式（简单版本，可根据需要扩展）
        phone_pattern = re.compile(r'^1[3-9]\d{9}$')
        # 用于识别日期的正则表达式（简单版本，匹配YYYY-MM-DD、YYYY/MM/DD、YYYY_MM_DD等格式）
        date_pattern = re.compile(r'^\d{4}[-_/]\d{1,2}[-_/]\d{1,2}$')
        
        for col_idx, col in enumerate(df.columns):
            # 获取该列的非空值样本
            non_empty_values = df[col].dropna().astype(str)
            if len(non_empty_values) == 0:
                new_name = f'column_{col_idx+1}'
                new_columns.append(new_name)
                continue
            
            # 分析样本特征
            sample_values = non_empty_values.head(min(10, len(non_empty_values)))
            
            # 判断是否是电话列
            is_phone = all(phone_pattern.match(str(val)) for val in sample_values)
            if is_phone and 'phone' not in used_names:
                new_name = 'phone'
                used_names.add(new_name)
                new_columns.append(new_name)
                continue
            
            # 判断是否是日期列
            is_date = all(date_pattern.match(str(val)) for val in sample_values)
            if is_date and 'date' not in used_names:
                new_name = 'date'
                used_names.add(new_name)
                new_columns.append(new_name)
                continue
            
            # 判断是否可能是姓名列（中文名字特征：2-4个汉字）
            chinese_name_pattern = re.compile(r'^[\u4e00-\u9fa5]{2,4}$')
            is_chinese_name = all(chinese_name_pattern.match(str(val)) for val in sample_values)
            if is_chinese_name and 'name' not in used_names:
                new_name = 'name'
                used_names.add(new_name)
                new_columns.append(new_name)
                continue
            
            # 判断是否是纯数字列（可能是ID、编号等）
            is_numeric = all(str(val).isdigit() for val in sample_values)
            if is_numeric and 'id' not in used_names:
                new_name = 'id'
                used_names.add(new_name)
                new_columns.append(new_name)
                continue
            
            # 判断是否可能是状态或类别列（文本较短，重复值较多）
            if len(sample_values) > 0:
                # 计算唯一值比例
                unique_ratio = len(sample_values.unique()) / len(sample_values)
                # 如果唯一值比例低且文本较短，可能是状态列
                if unique_ratio < 0.5 and all(len(str(val)) < 20 for val in sample_values) and 'status' not in used_names:
                    new_name = 'status'
                    used_names.add(new_name)
                    new_columns.append(new_name)
                    continue
            
            # 默认命名方案
            counter = 1
            base_name = 'remark'
            new_name = base_name
            while new_name in used_names:
                new_name = f'{base_name}_{counter}'
                counter += 1
            used_names.add(new_name)
            new_columns.append(new_name)
        
        # 记录推断的列名，但不修改df的列名（由调用方法处理）
        self.logs.append(f"🔍 智能推断的列名: {new_columns}")
        return new_columns

    def _clean_column_names(self, columns):
        """清洗列名：去除特殊字符、空格，替换为下划线，避免SQL语法错误"""
        cleaned = []
        for col in columns:
            # 去除前后空格，替换中间空格/特殊字符为下划线
            clean_col = re.sub(r'[\s\W]+', '_', str(col).strip())
            # 去除开头/结尾的下划线
            clean_col = clean_col.strip('_')
            # 若列名为空，自动命名为col_序号
            if not clean_col:
                clean_col = f"col_{len(cleaned) + 1}"
            cleaned.append(clean_col)
        self.logs.append(f"🔧 清洗后列名：{cleaned}")
        return cleaned

    def _infer_column_type(self, series):
        """推断列的数据类型，映射为SQLite类型（TEXT/INTEGER/REAL/DATE）"""
        import re
        
        # 处理空值列（全部为NaN）
        if series.isna().all():
            return "TEXT"
        
        # 优先检查是否为电话号码列（11位手机号码格式）
        phone_pattern = re.compile(r'^1[3-9]\d{9}$')
        try:
            # 将非空值转为字符串并检查是否匹配电话号码格式
            is_phone = series.dropna().astype(str).apply(lambda x: bool(phone_pattern.match(str(x)))).all()
            if is_phone:
                return "TEXT"  # 电话号码作为文本存储
        except:
            pass
        
        # 尝试转换为整数类型
        try:
            # 排除浮点型（如2.0），仅纯整数
            if series.dropna().apply(lambda x: isinstance(x, int) or (isinstance(x, float) and x.is_integer())).all():
                return "INTEGER"
        except:
            pass
        
        # 尝试转换为浮点型
        try:
            pd.to_numeric(series.dropna(), errors='raise')
            return "REAL"
        except:
            pass
        
        # 尝试转换为日期类型（在数值类型之后，避免将数值错误识别为日期）
        try:
            pd.to_datetime(series.dropna(), errors='raise')
            return "TEXT"  # SQLite无DATE类型，用TEXT存储（ISO格式）
        except:
            pass
        
        # 默认文本类型
        return "TEXT"

    def _generate_create_table_sql(self):
        """根据DataFrame生成SQL建表语句"""
        # 推断每列的数据类型
        column_types = {col: self._infer_column_type(self.df[col]) for col in self.df.columns}
        self.logs.append(f"📋 列类型推断结果：{column_types}")
        
        # 拼接SQL字段（列名 类型）
        columns_sql = ", ".join([f"`{col}` {dtype}" for col, dtype in column_types.items()])
        
        # 生成建表SQL（IF NOT EXISTS 避免重复创建）
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS `{self.table_name}` (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns_sql},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        return create_sql.strip()

    def _process_data(self):
        """处理数据：转换日期格式、处理空值"""
        import re
        
        df_processed = self.df.copy()
        
        for col in df_processed.columns:
            # 处理日期列（转换为ISO格式字符串）
            try:
                # 检查是否为电话号码列（避免将电话号码转换为日期）
                phone_pattern = re.compile(r'^1[3-9]\d{9}$')
                is_phone = False
                try:
                    # 采样检查是否为电话号码列
                    non_empty_values = df_processed[col].dropna()
                    if len(non_empty_values) > 0:
                        sample_size = min(5, len(non_empty_values))
                        sample_values = non_empty_values.head(sample_size).astype(str)
                        is_phone = all(bool(phone_pattern.match(str(val))) for val in sample_values)
                except:
                    pass
                
                # 如果不是电话号码列，才尝试日期转换
                if not is_phone and self._infer_column_type(df_processed[col]) == "TEXT":
                    # 尝试转换为日期
                    df_processed[col] = pd.to_datetime(df_processed[col], errors='ignore')
                    # 对成功转换的日期，根据原始数据精度动态调整格式
                    # 只输出日期部分，不添加T00:00:00
                    df_processed[col] = df_processed[col].apply(
                        lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) and isinstance(x, datetime) else x
                    )
            except:
                pass
        
        # 处理空值（替换为None，SQLite中存储为NULL）
        df_processed = df_processed.where(pd.notna(df_processed), None)
        return df_processed

    def export(self):
        """执行导出：创建数据库、建表、插入数据"""
        conn = None
        cursor = None
        try:
            # 1. 连接SQLite数据库（不存在则自动创建）
            self.logs.append(f"🔄 正在连接/创建SQLite数据库：{self.sqlite_path}")
            conn = sqlite3.connect(self.sqlite_path)
            # 设置更严格的错误处理模式
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA synchronous = NORMAL")
            cursor = conn.cursor()
            self.logs.append(f"📦 成功连接/创建SQLite数据库：{self.sqlite_path}")
            
            try:
                # 2. 生成并执行建表SQL
                # 为确保表结构正确，先删除已存在的同名表
                cursor.execute(f"DROP TABLE IF EXISTS `{self.table_name}`")
                conn.commit()
                
                create_sql = self._generate_create_table_sql()
                self.logs.append(f"⚙️  建表SQL：\n{create_sql}")
                cursor.execute(create_sql)
                conn.commit()
                self.logs.append(f"✅ 成功创建表：{self.table_name}")
                
                # 3. 处理数据（日期、空值）
                try:
                    df_processed = self._process_data()
                    self.logs.append(f"📋 数据预处理完成，准备插入")
                    
                    # 4. 批量插入数据
                    if len(df_processed) > 0:
                        # 生成插入SQL，只插入Excel中的列数据，id和created_at由数据库自动生成
                        columns = ", ".join([f"`{col}`" for col in df_processed.columns])
                        placeholders = ", ".join(["?" for _ in df_processed.columns])
                        insert_sql = f"INSERT INTO `{self.table_name}` ({columns}) VALUES ({placeholders})"
                        self.logs.append(f"🔧 插入SQL：{insert_sql[:100]}..." if len(insert_sql) > 100 else f"🔧 插入SQL：{insert_sql}")
                        
                        # 转换DataFrame为元组列表（SQLite插入格式）
                        data_tuples = []
                        for row in df_processed.values:
                            # 处理可能的None值和特殊类型
                            processed_row = []
                            for val in row:
                                if pd.isna(val):
                                    processed_row.append(None)
                                elif isinstance(val, datetime):
                                    processed_row.append(val.strftime('%Y-%m-%d'))
                                else:
                                    processed_row.append(val)
                            data_tuples.append(tuple(processed_row))
                        
                        # 批量执行插入（效率远高于循环插入）
                        self.logs.append(f"📊 准备插入 {len(data_tuples)} 条数据")
                        cursor.executemany(insert_sql, data_tuples)
                        conn.commit()
                        
                        self.logs.append(f"✅ 成功插入 {cursor.rowcount} 条数据")
                    else:
                        self.logs.append("ℹ️  无数据可插入（Excel表格为空）")
                    
                    # 5. 验证数据（可选：查询前5条数据）
                    try:
                        cursor.execute(f"SELECT * FROM `{self.table_name}` LIMIT 5")
                        sample_data = cursor.fetchall()
                        if sample_data:
                            self.logs.append(f"📝 数据样例（前5条）：")
                            # 获取实际的列名（包括自动生成的id和created_at）
                            cursor.execute(f"PRAGMA table_info(`{self.table_name}`)")
                            table_columns = [col[1] for col in cursor.fetchall()]
                            for row in sample_data:
                                row_dict = dict(zip(table_columns, row))
                                # 格式化输出，避免过长
                                formatted_row = {}
                                for k, v in row_dict.items():
                                    v_str = str(v)
                                    if len(v_str) > 50:  # 限制输出长度
                                        v_str = v_str[:50] + "..."
                                    formatted_row[k] = v_str
                                self.logs.append(formatted_row)
                    except Exception as verify_error:
                        self.logs.append(f"⚠️  数据验证时发生警告：{str(verify_error)}")
                except Exception as data_error:
                    conn.rollback()
                    raise RuntimeError(f"数据处理失败：{str(data_error)}")
                    
            except Exception as table_error:
                conn.rollback()
                raise RuntimeError(f"表创建/操作失败：{str(table_error)}")
                
        except Exception as e:
            # 确保连接被关闭
            if 'conn' in locals() and conn:
                try:
                    conn.rollback()
                except:
                    pass
            error_msg = f"导出失败：{str(e)}"
            self.logs.append(f"❌ {error_msg}")
            # 即使出错也要打印日志
            self._print_logs()
            raise RuntimeError(error_msg)
        finally:
            # 确保资源被释放
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass
                
        self.logs.append(f"🔚 导出完成！SQLite文件路径：{self.sqlite_path}")
        
        # 打印所有日志
        self._print_logs()
        
        return self.sqlite_path  # 返回生成的数据库路径，便于链式调用

    def _print_logs(self):
        """打印执行日志"""
        print("\n" + "="*50)
        print("📊 Excel转SQLite执行日志")
        print("="*50)
        for log in self.logs:
            print(log)
        print("="*50 + "\n")

# -------------------------- 示例使用 --------------------------
if __name__ == "__main__":
    print("🚀 ExcelToSQLite 工具启动")
    print("📚 提供以下功能：")
    print("  1. 单个Excel文件转换（默认将第一行作为数据而非表头）")
    print("  2. 智能列名推断：自动识别姓名、电话、日期等信息，生成name、phone等有意义的列名")
    print("  3. 自动为每行数据生成连续唯一的ID")
    print("  4. 自动搜索目录下所有Excel文件并批量转换")
    print()
    
    # 示例1：转换单个Excel文件（默认将第一行作为数据，自动推断列名）
    # 取消注释下面的代码块即可使用
    # print("\n=== 示例1：转换单个Excel文件（自动处理） ===")
    # try:
    #     EXCEL_PATH = "data.xlsx"  # 你的Excel文件路径（必填）
    #     SQLITE_PATH = "mydatabase.db"  # 输出的SQLite文件路径（可选）
    #     TABLE_NAME = "mytable"  # 数据表名（可选）
    #     SHEET_NAME = 0  # 读取的sheet（0=第一个sheet，可传sheet名如"用户数据"）
    #     
    #     # 创建转换器实例（默认has_header=False，将第一行作为数据处理）
    #     converter = ExcelToSQLite(
    #         excel_path=EXCEL_PATH,
    #         sqlite_path=SQLITE_PATH,
    #         table_name=TABLE_NAME,
    #         sheet_name=SHEET_NAME
    #         # has_header=False  # 默认值，自动推断列名
    #     )
    #     
    #     # 执行导出
    #     db_path = converter.export()
    #     print(f"📌 数据库已生成：{db_path}")
    #     print(f"✅ 已自动为每行数据生成连续唯一ID")
    #     print(f"✅ 已智能推断列名（如name、phone、date等）")
    # except Exception as e:
    #     print(f"\n❌ 错误：{str(e)}")
    
    # 示例2：强制将第一行作为表头（当Excel文件确实有表头时使用）
    # 取消注释下面的代码块即可使用
    # print("\n=== 示例2：将第一行作为表头处理 ===")
    # try:
    #     converter = ExcelToSQLite(
    #         excel_path="data_with_header.xlsx",
    #         has_header=True,  # 明确指定文件有表头
    #         table_name="data_with_original_headers"  # 自定义表名
    #     )
    #     converter.export()
    # except Exception as e:
    #     print(f"\n❌ 错误：{str(e)}")
    
    # 示例3：批量转换目录下所有Excel文件到独立数据库
    print("\n=== 示例3：批量转换目录下所有Excel文件 ===")
    try:
        # 批量转换当前目录下的excel文件夹中的所有Excel文件
        EXCEL_DIR = os.path.join(os.path.dirname(__file__), "excel")
        print(f"🔍 正在扫描目录：{EXCEL_DIR}")
        
        # 方案A：每个Excel文件生成独立的数据库文件
        print("\n📋 方案A：每个Excel文件生成独立数据库")
        ExcelToSQLite.batch_convert_directory(EXCEL_DIR)
        
        # 方案B：所有Excel文件转换到同一个数据库（取消注释使用）
        # print("\n📋 方案B：所有Excel文件转换到同一个数据库")
        # OUTPUT_DB = os.path.join(EXCEL_DIR, "all_excel_data.db")
        # ExcelToSQLite.batch_convert_directory(EXCEL_DIR, OUTPUT_DB)
        # print(f"\n📌 所有Excel数据已合并到：{OUTPUT_DB}")
        
    except FileNotFoundError as e:
        print(f"\n❌ 目录不存在：{str(e)}")
    except Exception as e:
        print(f"\n❌ 批量转换失败：{str(e)}")
    
    print("\n🎉 任务完成！")
    print("💡 使用说明：")
    print("  - 默认行为：将Excel的第一行作为数据处理，自动推断列名为name、phone、date等")
    print("  - 如需将第一行作为表头：设置 has_header=True 参数")
    print("  - 智能列名识别：自动检测姓名（中文）、电话（11位手机号）、日期、ID等数据类型")
    print("  - 电话格式保护：优先识别11位手机号码格式，避免错误转换为时间戳")
    print("  - 日期格式优化：日期会以纯YYYY-MM-DD格式显示，不包含T00:00:00时间信息")
    print("  - 自动生成连续ID：每条记录都会有唯一的自增主键ID")
    print("  - 自定义表名：通过 table_name 参数设置数据表名称")
    print("  - 批量处理：使用 batch_convert_directory 方法处理目录下所有Excel文件")