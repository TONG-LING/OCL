import os
import re
import sys
import logging
import psutil
import threading
from link import link_files
from link import add_files
from info import info_command
from recover import handle_recover_command
from patch_scn import pscn


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



OFFSET_VERSION = 0x64397E
OFFSET_SID = 0x2020

EXCLUDED_DIRS = {"proc", "sys", "dev", "run"}



# 设置日志
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.info("Command line tool initialization.")

def search_file(search_roots, target_filename, timeout=20):
    """在指定的搜索目录中查找文件，忽略大小写，并支持超时"""
    target_filename_lower = target_filename.lower()  # 统一转换为小写
    found_file = [None]  # 使用列表来存储找到的文件路径

    def search():
        for root in search_roots:
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    if filename.lower() == target_filename_lower:  # 忽略大小写比较
                        found_file[0] = os.path.join(dirpath, filename)  # 返回完整路径
                        return
    search_thread = threading.Thread(target=search)
    search_thread.start()
    search_thread.join(timeout)

    if search_thread.is_alive():
        print("Searching has timed out.")
        return None  # 超时未找到
    else:
        return found_file[0]  # 返回找到的文件路径或 None


def get_search_roots():
    """获取不同系统下的搜索根目录"""
    if os.name == 'nt':  # Windows
        drives = [d.device for d in psutil.disk_partitions()]
        # 先构造所有盘符下的 `app` 目录
        app_dirs = [os.path.join(drive, "app") for drive in drives]
        # 再添加整个盘符（作为后备搜索路径）
        return app_dirs + drives
    else:  # Linux/macOS
        return ["/", "/mnt", "/media", "/Volumes"]  # 扩展搜索范围



def read_file_offset(file_path, offset, size):
    """从文件特定偏移量读取数据"""
    try:
        with open(file_path, "rb") as f:
            f.seek(offset)
            return f.read(size)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return None


def show_database_info(file_path):
    """读取并显示数据库信息"""
    print("\n[INFO] Found system file")

    version_data = read_file_offset(file_path, OFFSET_VERSION, 11)
    if version_data:
        version_str = version_data.decode(errors='ignore').strip()  # 去除前后空格
        print(f"Oracle Version: {version_str}")

    endianness_data = b'\x01\x00'  # 示例数据，表示小端格式
    if endianness_data:
        endianness = int.from_bytes(endianness_data, 'little')  # 直接转换
        print(f"Endianness: {'Little Endian' if endianness == 0x01 else 'Big Endian'}")

    sid_data = read_file_offset(file_path, OFFSET_SID, 8)
    if sid_data:
        sid_str = sid_data.decode(errors="ignore").strip()  # 去除前后空格
        sid_str = re.sub(r"[^\x20-\x7E]", "", sid_str)  # 过滤非可打印字符
        if sid_str:  # 只有在非空时才打印
            print(f"Database SID: {sid_str}")


def show_help():
    """显示帮助信息"""
    print("Available commands:")
    print("  help       - Show this help message")
    print("  scan       - Scan for system file and show database info")
    print("  link       - Data file information is displayed through control files and system files")
    print("  info       - Displays the latest file information and status")
    print("  recover    - recover the file header/block, for example, recover datafile [fno]/recover block fno,block_no")
    print("  random     - Block random destruction,prohibited use")
    print("  logan*     - Retrieve errors in log files and give solutions")
    print("  dump*      - Extract the tables in the data file")
    print("  pscn*      - Push the scn number in memory,ORA-00600[266X]")
    print("  exit       - Exit the program")
    print("----------------------------------------")
    print("Those marked with * are standalone tools")

def print_boxed_message(message):
    border = "*" * (len(message) + 4)  # 计算边框的长度
    print(border)
    print(f"* {message} *")
    print(border)

class OCLShell:
    """交互式命令行工具"""

    def __init__(self):
        self.file_path = None
        self.db_files_linked = False  # 标记 db_files 是否已通过 link_files 更新
        self.db_files_add = False
        print_boxed_message("Oracle Recover Command Line Tool (Single instance)")
        print("FOR TESTING PURPOSES ONLY, IF THE DATABASE IS OPEN, IT WILL CAUSE INCALCULABLE CONSEQUENCES!")
        print("Scanning for system file...")
        search_roots = get_search_roots()
        self.file_path = search_file(search_roots, "system01.dbf")

        attempts = 0  # 定义尝试次数
        while not self.file_path:  # 让用户手动输入，直到找到正确路径
            if attempts > 0:
                print("[ERROR] system file not found!")
            user_input = input("Please enter the full path to system.dbf (or press Enter to stop): ").strip()
            if user_input == "":  # 用户输入回车
                print("Exiting the search.")
                break  # 用户按回车，直接退出循环
            if os.path.exists(user_input) and user_input.lower().endswith(".dbf"):
                self.file_path = user_input
            else:
                print("[ERROR] Invalid file path. Please check and try again.")
                attempts += 1  # 计数无效输入的尝试次数

        # 此处不再需要 continue
        if self.file_path:
            show_database_info(self.file_path)

    def run(self):
        """主交互循环"""
        while True:
            try:
                command = input("\nOCL> ").strip().replace("\r", "").lower()
                if not command:  # 如果用户只按回车，直接重新显示 OCL>
                    continue
                if command == "help":
                    show_help()
                elif command == "scan":
                    self.file_path = search_file("/", "system01.dbf")
                    if self.file_path:
                        show_database_info(self.file_path)
                    else:
                        print("[ERROR] system file not found!")

                elif command.startswith("recover"):
                     if self.file_path or self.db_files_add:
                            handle_recover_command(command.split(' ', 1)[1])  # 传入剩余命令部分
                     else:
                            print("[ERROR] No database file found. Please scan first.")

                elif command.startswith("link"):
                    parts = command.split()
                    if self.file_path and len(parts) == 1:
                        # 这里可以根据需要处理其他参数
                        link_files(self.file_path)  # 调用 link.py 里的方法
                        self.db_files_linked = True  # 设置为 True，标记已链接
                    elif len(parts) > 1:  # 如果有超过一个部分，说明有额外内容
                         if add_files(parts[1:]) is not None:
                            self.db_files_linked = True  # 设置为 True，标记已链接
                            self.db_files_add = True
                    else:
                        print("[ERROR] system file not found. Please scan first.")

                elif command == "info":
                    if not self.db_files_linked:
                        print("[ERROR] Please run the 'link' command first to link the database files.")
                    else:
                        info_command()  # 直接调用 info.py 里的方法

                elif command == "pscn":
                    pscn()
                elif command == "random":
                    print("Not implemented yet!")
                elif command == "dump":
                    print("Not implemented yet!")
                elif command == "logan":
                    print("Not implemented yet!")
                elif command == "exit":
                    print("Exiting OCL. Goodbye!")
                    break
                else:
                    print("Unknown command. Type 'help' for a list of commands.")
            except KeyboardInterrupt:
                print("\nExiting OCL. Goodbye!")
                break


if __name__ == "__main__":
    shell = OCLShell()
    shell.run()
