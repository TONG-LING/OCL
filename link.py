import os
import re
import sys
import logging

# 偏移量定义
OFFSETS = {
    "FNO": 0x2034,
    "DBID": 0x201C,
    "FUZZY": 0x208A,
    "R_SCN": 0x2074,
    "CKP_SCN_BAS": 0x21E4,
    "CKP_SCN_WRP": 0x21E8,
    "TS_NAME": 0x2152,
    "R_C_SCN": 0x2070,
    "kcvfhcpc": 0x208C,
    "kcvfhccc": 0x2094,
    "kcvcptim": 0x20A0
}

# 获取当前程序所在的路径
if getattr(sys, 'frozen', False):  # 如果是 PyInstaller 打包后的环境
    BASE_DIR = sys._MEIPASS  # 获取 PyInstaller 解压后的临时路径
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 非 PyInstaller 环境时

# 日志和备份目录路径
BACKUP_DIR = "initial_backups"
LOG_DIR = os.path.join(BASE_DIR, "log")  # 确保日志目录在当前目录或解压后目录
LOG_FILE = os.path.join(LOG_DIR, "recover.log")

# 确保日志和备份目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# 设置日志
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.info("Link module to complete.")


# 存储数据库文件信息
class DBFile:
    def __init__(self, path):
        self.path = path
        self.fno = None
        self.dbid = None
        self.fuzzy = None
        self.r_scn = None
        self.ckp_scn_bas = None
        self.ckp_scn_wrp = None
        self.ts_name = None

    def read_file_offset(self, file_path, offset, size):
        """从文件特定偏移量读取数据"""
        try:
            with open(file_path, "rb") as f:
                f.seek(offset)
                return f.read(size)
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")
            return None

    def extract_metadata(self):
        """提取 DBF 文件的所有元数据"""
        self.fno = str(int.from_bytes(self.read_file_offset(self.path, OFFSETS["FNO"], 1), byteorder="little"))
        self.dbid = str(int.from_bytes(self.read_file_offset(self.path, OFFSETS["DBID"], 4), byteorder="little"))
        self.fuzzy = int.from_bytes(self.read_file_offset(self.path, OFFSETS["FUZZY"], 2), byteorder="little")

        file_name = os.path.basename(self.path).lower()
        if "system" in file_name:
            self.fuzzy = "no" if self.fuzzy == 0x2000 else "yes"
        else:
            self.fuzzy = "no" if self.fuzzy == 0x0000 else "yes"

        self.r_scn = str(int.from_bytes(self.read_file_offset(self.path, OFFSETS["R_SCN"], 4), byteorder="little"))
        self.ckp_scn_wrp = str(int.from_bytes(self.read_file_offset(self.path, OFFSETS["CKP_SCN_WRP"], 4), byteorder="little"))
        self.ckp_scn_bas = str(int.from_bytes(self.read_file_offset(self.path, OFFSETS["CKP_SCN_BAS"], 4), byteorder="little"))
        scn_total = int(self.ckp_scn_wrp) * (2 ** 32) + int(self.ckp_scn_bas)
        self.ckp_scn_bas = str(scn_total)
        self.ts_name = self.read_file_offset(self.path, OFFSETS["TS_NAME"], 30).decode("utf-8").strip("\x00").strip()

    def __str__(self):
        """返回 DBFile 对象的字符串表示"""
        return f"FNO: {self.fno}, DBID: {self.dbid}, PATH: {self.path}, FUZZY: {self.fuzzy}, R_SCN: {self.r_scn}, CKP_SCN: {self.ckp_scn_bas}, TS_NAME: {self.ts_name}"


def find_control_file(directory):
    global control_file_exist
    """查找 control01.ctl 或 control02.ctl 文件"""
    control_file_exist = False  # 初始化为 False
    pattern = re.compile(r"^control\d+\.ctl$", re.IGNORECASE)  # 正则表达式模式
    for root, _, files in os.walk(directory):
        for file in files:
            if pattern.match(file):  # 使用正则表达式匹配文件名
                control_file_exist = True  # 找到文件，设置标志为 True
                return os.path.join(root, file)  # 返回文件的完整路径
    return None  # 未找到文件时返回 None


def scan_control_file(control_file):
    """使用 Python 直接解析控制文件，提取 .dbf 文件路径，并去重"""
    db_files = set()  # 使用集合去重

    try:
        with open(control_file, "rb") as f:
            data = f.read()

        # 使用正则匹配 .dbf 文件路径
        matches = re.findall(rb'[a-zA-Z]:\\[\w\\.-]+\.dbf|[\w./-]+\.dbf', data, re.IGNORECASE)

        # 去重并转换为字符串，并排除包含 "temp" 的路径
        for match in matches:
            dbf_path = match.decode("utf-8", errors="ignore").strip()
            if "temp" not in dbf_path.lower():  # 直接排除 temp 文件
                db_files.add(dbf_path)

    except Exception as e:
        print(f"Error reading control file {control_file}: {e}")

    return [DBFile(path) for path in db_files]


# 全局变量 db_files，用于存储扫描的数据库文件信息
control_file_exist = False
db_files = []
reference_file=[]
control_file = []
def link_files(system_dbf_path):
    global control_file
    global reference_file
    global control_file_exist
    """核心函数：查找 control 文件并提取信息"""
    if not system_dbf_path:
        print("Error: system_dbf_path is None")
        return
    print(f"Reference file: {system_dbf_path}")
    reference_file=system_dbf_path
    # 获取 system.dbf 所在目录
    system_dir = os.path.dirname(system_dbf_path)
    control_file = find_control_file(system_dir)

    if not control_file:
        print("Error: No control file found in system.dbf directory")
        return

    db_files = scan_control_file(control_file)
    globals()["db_files"] = db_files  # 直接更新全局变量

    # 读取偏移量数据
    for db_file in db_files:
        db_file.extract_metadata()


    # 计算每列的最大宽度
    max_lengths = {
            "FNO": max(len("FNO"), max(len(item.fno or 'N/A') for item in db_files)),
            "DBID": max(len("DBID"), max(len(item.dbid or 'N/A') for item in db_files)),
            "PATH": max(len("PATH"), max(len(item.path) for item in db_files)),
            "FUZZY": max(len("FUZZY"), max(len(item.fuzzy or 'N/A') for item in db_files)),
            "R_SCN": max(len("R_SCN"), max(len(item.r_scn or 'N/A') for item in db_files)),
            "CKP_SCN": max(len("CKP_SCN"), max(len(item.ckp_scn_bas or 'N/A') for item in db_files)),
            "TS_NAME": max(len("TS_NAME"), max(len(item.ts_name or 'N/A') for item in db_files)),
    }

    # 打印表头
    header = f"| {{:<{max_lengths['FNO']}}} | {{:<{max_lengths['DBID']}}} | {{:<{max_lengths['PATH']}}} | {{:<{max_lengths['FUZZY']}}} | {{:<{max_lengths['R_SCN']}}} | {{:<{max_lengths['CKP_SCN']}}} | {{:<{max_lengths['TS_NAME']}}} |"
    print("-" * (sum(max_lengths.values()) + 7 * 3))
    print(header.format("FNO", "DBID", "PATH", "FUZZY", "R_SCN", "CKP_SCN", "TS_NAME"))
    print("-" * (sum(max_lengths.values()) + 7 * 3))

    # 打印数据行
    for db_file in db_files:
        print(
            f"| {db_file.fno or 'N/A':<{max_lengths['FNO']}} | "
            f"{db_file.dbid or 'N/A':<{max_lengths['DBID']}} | "
            f"{db_file.path:<{max_lengths['PATH']}} | "
            f"{db_file.fuzzy or 'N/A':<{max_lengths['FUZZY']}} | "
            f"{db_file.r_scn or 'N/A':<{max_lengths['R_SCN']}} | "
            f"{db_file.ckp_scn_bas or 'N/A':<{max_lengths['CKP_SCN']}} | "
            f"{db_file.ts_name or 'N/A':<{max_lengths['TS_NAME']}} |"
        )

    print("-" * (sum(max_lengths.values()) + 7 * 3))  # 打印分隔线




#    print(f"Updated db_files: {db_files}")  # 打印 db_files 的内容
def update_db_files():
    """重新扫描数据库文件，更新 db_files 全局变量"""
    global db_files  # 需要声明全局变量
    if not db_files:
        print("No database files found. Please run 'link' first.")
        return
    # 重新解析元数据
    for db_file in db_files:
        db_file.extract_metadata()
    print("\n[INFO] Database files info updated successfully.\n")


def add_files(file_paths):
    """添加新的 DBF 文件到 db_files 列表并提取其元数据"""
    global db_files  # 声明全局变量
    new_files = []

    for path in file_paths:
        # 清理路径，去除不可见字符
        clean_path = re.sub(r'[\u200B-\u200D\u202A-\u202E]', '', path.strip())

        # 检查路径是否有效
        if os.path.isfile(clean_path):
            db_file = DBFile(clean_path)
            db_file.extract_metadata()  # 提取元数据
            new_files.append(db_file)  # 添加到新的文件列表
        else:
            print(f"[WARNING] File not found: {clean_path}")
            return None

    # 将新文件添加到全局 db_files 列表
    db_files.extend(new_files)
    print("[INFO] Files added successfully.")
    return True

