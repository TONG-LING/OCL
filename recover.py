import os
import logging
import link
import sys
import struct
from ctl_ckp_cnt import find_file_fhcpc
from sum_apply import  calculate_checksum
# 偏移量定义
OFFSETS = {
    "FUZZY": (0x208A, 2),      # 读取 2 个字节
    "CKP_SCN_BAS": (0x21E4, 4),    # 读取 4 个字节
    "CKP_SCN_BAS": (0x21E8, 4),    # 读取 4 个字节
    "R_SCN": (0x2074, 4),      # 读取 4 个字节
    "R_C_SCN": (0x2070, 4),    # 读取 4 个字节
    "kcvfhcpc": (0x208C, 4),   # 读取 4 个字节
    "frmt_kcbh": (0x2001, 1),   # 读取 4 个字节
    "kcvfhccc": (0x2094, 4),   # 读取 4 个字节
    "kcvcptim": (0x20A0, 4),  # 读取 4 个字节
    "kccfhcsq": (0x2028, 4)
}

OFFSETS_BLOCK = {
    "type_kcbh": (0x0, 1),  # 读取 1 个字节
    "frmt_kcbh": (0x1, 1),   # 读取 4 个字节
    "seq_kcbh": (0xE, 1),   # 读取 1 个字节
    "bas_kcbh": (0x8, 4),   # 读取 4 个字节
    "tailchk": (0x1FFC, 4),    # 读取 4 个字节
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




BACKUP_SIZE = 16384 # 备份前 40,960 字节 (0xA000)

# 设置日志
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.info("Recover script initialized.")

def get_backup_path(dbf_path):
    """生成备份文件路径"""
    filename = os.path.basename(dbf_path)
    return os.path.join(BACKUP_DIR, filename.replace(".dbf", "bak.dbf"))


def read_offset(file_path, offset, size):
    """从文件的偏移量处读取指定大小的数据"""
    try:
        with open(file_path, "rb") as f:
            f.seek(offset)
            return f.read(size)  # 读取指定字节数
    except Exception as e:
        print(f"Failed to read {file_path} at offset {offset}: {e}")
        return None


def write_offset(file_path, offset, data):
    """在文件的偏移量处写入数据（小端存储）"""
    try:
        with open(file_path, "r+b") as f:
            f.seek(offset)
            f.write(data)
        logging.info(f"Successfully wrote to {file_path} at offset {offset}")
    except Exception as e:
        logging.error(f"Failed to write {file_path} at offset {offset}: {e}")

def backup_file(db_file):
    """备份单个 .dbf 文件的前 40,960 字节"""
    backup_path = get_backup_path(db_file.path)
    if os.path.exists(backup_path):
        logging.info(f"Backup already exists for {db_file.path}, skipping backup.")
        return
    try:
        with open(db_file.path, "rb") as f:
            data = f.read(BACKUP_SIZE)
        with open(backup_path, "wb") as f:
            f.write(data)
        logging.info(f"Backup created: {backup_path}")
    except Exception as e:
        logging.error(f"Failed to backup {db_file.path}: {e}")

def backup_files(target_file=None):
    """根据文件号从 db_files 中找到对应的文件"""
    if target_file is not None:  # Check if a specific file is specified
        # Find the corresponding file object by fno
        db_file = get_file_by_number(link.db_files, target_file)
        if db_file:
            backup_file(db_file)
            #print(f"[INFO] Backed up file: {db_file.path}")
        else:
            print(f"[ERROR] No file found with fno {target_file}.")
    else:
        for db_file in link.db_files:  # Backup all files
            backup_file(db_file)
            print(f"[INFO] Backed up file: {db_file.path}")



def get_file_by_number(db_files, file_number):
    """根据文件号从 db_files 中找到对应的文件"""
    if not file_number:
        return None  # 如果没有输入文件号，返回 None

    # 遍历 db_files，查找与输入的文件号匹配的文件
    for db in db_files:
        if str(db.fno) == str(file_number):  # 以字符串形式比较，防止数据类型不匹配
            return db  # 找到匹配的文件，返回文件信息

    # 如果没有找到匹配的文件，返回 None
    return None


def recover_files(target_file=None):
    """执行 recover 操作"""

    import link
    db_files = link.db_files  # 获取最新的 db_files

    if not db_files:
        print("Error: No database files found. Please run the 'link' command first.")
        return

    # 让用户输入文件号，如果用户没有输入（按回车），则选择默认的 system.dbf 文件
    file_number = input("Please enter the file fno as the reference value (system.dbf is selected by default):").strip()

    # 如果用户没有输入内容，使用默认的 system.dbf 文件
    if not file_number:
        print("No file fno is entered.  The system.dbf is selected as the reference value.")
        file_number = 1  # 默认值为 system.dbf

    # **通过文件号或默认选择 system.dbf 查找文件**
    system_dbf = get_file_by_number(db_files, file_number)

    if not system_dbf:
        print(f"Error: {file_number} File not found.")
        return

    print(f"Reference file:{system_dbf.path}")

    # **读取 system.dbf 作为基准值**
    system_values = {key: read_offset(system_dbf.path, info[0], info[1]) for key, info in OFFSETS.items()}
    # **备份目标文件**
    backup_files(target_file)

    # **修正 target_files 的逻辑**（将 target_file 转为字符串）
    target_files = [db for db in db_files if str(db.fno) == str(target_file)] if target_file else db_files

    if not target_files:
        print(f"Error: No database file found with FNO {target_file}")
        return

    # **执行修改**
    for db_file in target_files:
        print(f"Modifying {db_file.path}...")

        for key, (offset, size) in OFFSETS.items():
            if key == "FUZZY":
                # **修改 FUZZY 时的特殊处理**
                if "system" in db_file.path.lower():  # 如果是 system 文件
                    new_value = b"\x20\x00"  # 小端格式
                else:
                    new_value = b"\x00\x00"  # 其他文件

                # **日志记录 FUZZY 修改**
                logging.info(
                    f"Key: {key}, Offset: {hex(offset)}, Old Value: (not applicable), "
                    f"New Value: {new_value.hex()}"
                )
            elif key == "kcvfhcpc" and link.control_file_exist:
                # **调用 find_file_fhcpc 并打印结果**
                    fhcpc_value = find_file_fhcpc(db_file.path)
                    new_value = fhcpc_value



            elif key == "kcvfhccc" and link.control_file_exist:
                # **调用 find_file_fhcpc 并打印结果**
                fhcpc_value = find_file_fhcpc(db_file.path)
                # **确保 fhcpc_value 是 bytes 且长度正确**
                if not isinstance(fhcpc_value, bytes) or len(fhcpc_value) != 4:
                    logging.error(f"Invalid value for {key}: {fhcpc_value}")
                    continue
                    # **小端转换：bytes → int**
                fhcpc_int = int.from_bytes(fhcpc_value, byteorder="little")  # 解析小端
                fhccc_int = fhcpc_int - 1  # **减 1**
                new_value = fhccc_int.to_bytes(4, byteorder="little")  # **转换回小端 bytes**
                logging.info(
                    f"Key: {key}, Offset: {hex(offset)}, "
                    f"Old Value: {fhcpc_value.hex()}, New Value: {new_value.hex()}"
                )
            else:
                # **其他字段的处理**
                old_value = read_offset(db_file.path, offset, size)
                new_value = system_values[key][:size]

                # **日志记录**
                logging.info(
                    f"Key: {key}, Offset: {hex(offset)}, System Value: {new_value.hex()}, "
                    f"Old Value: {old_value.hex()}, New Value: {new_value.hex()}"
                )

            # **写入新值**
            write_offset(db_file.path, offset, new_value)

            # **计算 `block_no`**
            offset_decimal = int(offset)  # 确保 offset 是十进制整数
            if offset_decimal < 8192:
                logging.warning(f"Offset {offset_decimal} is invalid for block calculation.")
                return  # 直接返回，避免计算错误

            block_no = (offset_decimal - 8192) // 8192 + 1

            # **计算 `chkval_kcbh` 偏移量**
            chkval_kcbh_offset = 0x2010 + (block_no - 1) * 8192  # 计算当前块的 chkval 偏移量

            # **计算校验和**
            checksum_value = calculate_checksum(db_file.path, block_no=block_no)

            # **如果 checksum_value 是 0，可能是无改动**
            if checksum_value == 0x0000:
                logging.info(f"Checksum is 0x0000, indicating no changes in block {block_no}. Skipping update.")
            else:
                # **写入校验和**
                write_offset(db_file.path, chkval_kcbh_offset, checksum_value.to_bytes(2, "little"))
                logging.info(
                    f"Checksum {hex(checksum_value)} written to {db_file.path} at offset {hex(chkval_kcbh_offset)}.")

    print("Recover operation completed.")
    logging.info("Recover operation completed.")

    # **更新 db_files**
    link.update_db_files()
    logging.info("Updated db_files after recovery.")
    link.reference_file=system_dbf.path


def recover_block(fileno, blockno):
    """
    恢复指定文件和区块的数据，修复坏块并计算校验和。

    Args:
        fileno (int): 文件编号，用于查找文件路径。
        blockno (int): 数据块编号，用于查找并修复数据块。
        offset (int): 数据块的偏移量，用于计算校验和。
    """
    # 如果没有输入文件号，返回 None
    if not fileno:
        logging.error("File number (fileno) is required.")
        return None
    # 遍历 db_files，查找与输入的文件号匹配的文件
    db_files = link.db_files
    file_path_temp = get_file_by_number(db_files, fileno)
    file_path=file_path_temp.path
    if not file_path:
        # 如果没有找到文件，抛出异常
        logging.error(f"File with fileno {fileno} not found in db_files.")
        return None
    try:
        # 确保文件路径存在
        print(f"File :{file_path}")
        if not os.path.exists(file_path):
            logging.error(f"File {file_path} does not exist.")
            return None
        # 读取偏移量的相关数据
        seq_kcbh = read_offset(file_path,
                               (OFFSETS_BLOCK["seq_kcbh"][0] + (blockno - 1) * 8192+8192),
                               OFFSETS_BLOCK["seq_kcbh"][1])

        tailchk = read_offset(file_path,
                              (OFFSETS_BLOCK["tailchk"][0] + (blockno - 1) * 8192+8192),
                              OFFSETS_BLOCK["tailchk"][1])
        bas_kcbh = read_offset(file_path,
                               (OFFSETS_BLOCK["bas_kcbh"][0] + (blockno - 1) * 8192+8192),
                               OFFSETS_BLOCK["bas_kcbh"][1])
        type_kcbh = read_offset(file_path,
                                (OFFSETS_BLOCK["type_kcbh"][0] + (blockno - 1) * 8192+8192),
                                OFFSETS_BLOCK["type_kcbh"][1])

        # 确保读取的数据是字节类型
        if seq_kcbh is None or tailchk is None or bas_kcbh is None or type_kcbh is None:
            raise ValueError(f"Failed to read required data from {file_path}.")

        # tailchk = tailchk.hex()  # 0x02062CD9
        # bas_kcbh = bas_kcbh.hex()  #  0x2CD93801
        # seq_kcbh = seq_kcbh.hex()  # 01
        # type_kcbh = type_kcbh.hex()  # 06

        bas_kcbh = hex(struct.unpack("<I", bas_kcbh)[0])
        tailchk = hex(struct.unpack("<I", tailchk)[0])
        seq_kcbh = seq_kcbh.hex()
        type_kcbh = type_kcbh.hex()
        # print(f"tailchk:{tailchk}")
        # print(f"bas_kcbh:{bas_kcbh}")
        # print(f"seq_kcbh:{seq_kcbh}")
        # print(f"type_kcbh:{type_kcbh}")
        # 如果 seq_kcbh == 0xFF，标记为坏块
        if seq_kcbh == 0xFF:
            print(f"Block {blockno} is marked as corrupted,seq_kcbh is {seq_kcbh} Do you want to repair it? (y/n): ", end="")
            user_input = input().strip().lower()
            if user_input == 'y':
                # 执行修复
                seq_kcbh = 0x01  # 将 seq_kcbh 修改为 1

                # 转换 bas_kcbh 为整数
                bas_kcbh_int = int(bas_kcbh, 16)

                # 计算 bas_kcbh 的低 16 位部分
                low_16_bas_kcbh = bas_kcbh_int & 0xFFFF  # 提取低 16 位部分

                # 确保 type_kcbh 和 seq_kcbh 是整数
                type_kcbh = int(type_kcbh, 16)
                seq_kcbh = int(seq_kcbh, 16)

                # 拼接低 16 位部分 + type_kcbh + seq_kcbh
                new_tailchk_hex = f"{low_16_bas_kcbh:04x}{type_kcbh:02x}{seq_kcbh:02x}"

                # 计算新的校验和
                expected_tailchk = int(new_tailchk_hex, 16)

                expected_tailchk_bytes = struct.pack("<I", expected_tailchk)
                # print(expected_tailchk)

                # 写入修复数据
                write_offset(file_path, OFFSETS_BLOCK["seq_kcbh"][0] + (blockno - 1) * 8192 + 8192, struct.pack("<B", seq_kcbh))
                write_offset(file_path, OFFSETS_BLOCK["tailchk"][0] + (blockno - 1) * 8192 + 8192, expected_tailchk_bytes)
                write_offset(file_path, OFFSETS_BLOCK["frmt_kcbhf"][0] + (blockno - 1) * 8192 + 8192,struct.pack("<B", 0xA2))

                logging.info(f"Block {blockno} repaired successfully.")
                print(f"Block {blockno} repaired successfully.")


                chkval_kcbh_offset = 0x10 + (blockno - 1) * 8192 + 8192  # 计算当前块的 chkval 偏移量
                # **计算校验和**
                checksum_value = calculate_checksum(file_path, block_no=blockno)
                # **如果 checksum_value 是 0，可能是无改动**
                if checksum_value == 0x0000:
                    logging.info(f"Checksum is 0x0000, indicating no changes in block {blockno}. Skipping update.")
                else:
                    # **写入校验和**
                    write_offset(file_path, chkval_kcbh_offset, checksum_value.to_bytes(2, "little"))
                    logging.info(
                        f"Checksum {hex(checksum_value)} written to {file_path} at offset {hex(chkval_kcbh_offset)}.")

            else:
                print(f"Skipping repair for block {blockno}.")
                logging.info(f"Skipping repair for block {blockno}.")

        else:
            # 转换 bas_kcbh 为整数
            bas_kcbh_int = int(bas_kcbh, 16)

            # 计算 bas_kcbh 的低 16 位部分
            low_16_bas_kcbh = bas_kcbh_int & 0xFFFF  # 提取低 16 位部分

            # 确保 type_kcbh 和 seq_kcbh 是整数
            type_kcbh = int(type_kcbh, 16)
            seq_kcbh = int(seq_kcbh, 16)

            # 拼接低 16 位部分 + type_kcbh + seq_kcbh
            new_tailchk_hex = f"{low_16_bas_kcbh:04x}{type_kcbh:02x}{seq_kcbh:02x}"

            # 计算新的校验和
            expected_tailchk = int(new_tailchk_hex, 16)
            # print(expected_tailchk)  # 输出：3643540993

            if int(tailchk, 16) == expected_tailchk:
                print(f"Block {blockno} is not corrupted")
                logging.info(f"Block {blockno} is not corrupted.")
            else:
                print(f"Block {blockno} is corrupted,tailchk is {tailchk} Do you want to repair it? (y/n): ", end="")
                user_input = input().strip().lower()
                if user_input == 'y':
                    # 执行修复
                    seq_kcbh = 0x01  # 将 seq_kcbh 修改为 1

                    expected_tailchk_bytes = struct.pack("<I", expected_tailchk)
                    #print(expected_tailchk)
                    # 写入修复数据
                    write_offset(file_path, OFFSETS_BLOCK["seq_kcbh"][0] + (blockno - 1) * 8192+8192, struct.pack("<B", seq_kcbh))
                    write_offset(file_path, OFFSETS_BLOCK["tailchk"][0] + (blockno - 1) * 8192+8192, expected_tailchk_bytes)
                    write_offset(file_path, OFFSETS_BLOCK["frmt_kcbhf"][0] + (blockno - 1) * 8192 + 8192,struct.pack("<B", 0xA2))

                    logging.info(f"Block {blockno} repaired successfully.")
                    print(f"Block {blockno} repaired successfully.")

                    chkval_kcbh_offset = 0x10 + (blockno - 1) * 8192 + 8192  # 计算当前块的 chkval 偏移量
                    # **计算校验和**
                    checksum_value = calculate_checksum(file_path, block_no=blockno)
                    # **如果 checksum_value 是 0，可能是无改动**
                    if checksum_value == 0x0000:
                        logging.info(f"Checksum is 0x0000, indicating no changes in block {blockno}. Skipping update.")
                    else:
                        # **写入校验和**
                        write_offset(file_path, chkval_kcbh_offset, checksum_value.to_bytes(2, "little"))
                        logging.info(
                            f"Checksum {hex(checksum_value)} written to {file_path} at offset {hex(chkval_kcbh_offset)}.")
                else:
                    print(f"Skipping repair for block {blockno}.")
                    logging.info(f"Skipping repair for block {blockno}.")

    except Exception as e:
        logging.error(f"Error while recovering block {blockno} from file {fileno}: {e}")
        print(f"Error while recovering block {blockno}: {e}")


def rollback_file(db_file):
    """回滚单个 .dbf 文件"""
    backup_path = get_backup_path(db_file.path)

    if not os.path.exists(backup_path):
        logging.warning(f"No backup found for {db_file.path}, skipping rollback.")
        return

    try:
        with open(backup_path, "rb") as f:
            data = f.read()

        with open(db_file.path, "r+b") as f:
            f.seek(0)
            f.write(data)

        logging.info(f"Rolled back: {db_file.path}")
    except Exception as e:
        logging.error(f"Failed to rollback {db_file.path}: {e}")

def rollback_files(target_file=None):
    """回退所有 .dbf 文件（或指定文件）"""
    if target_file:
        db_file = db_files[target_file - 1]
        rollback_file(db_file)
    else:
        for db_file in db_files:
            rollback_file(db_file)

    logging.info("Rollback completed.")

def handle_recover_command(command):
    """处理恢复命令"""
    command = command.strip().lower()

    if command == "all":
        recover_files()
    elif command.startswith("datafile") and len(command.split()) == 2:
        try:
            datafile_index = int(command.split()[1])
            recover_files(datafile_index)
        except ValueError:
            logging.error("Invalid datafile number. Please provide a valid integer.")
    elif command.startswith("block") and len(command.split()) == 2:
        try:
            # 获取 `recover block` 后面的部分
            _, blocks = command.split()
            # 分割 `fileno,blockno`，并将它们转为整数
            fileno, blockno = map(int, blocks.split(','))  # 这里确保 `blocks` 用逗号分割
            # 调用恢复块的函数
            recover_block(fileno, blockno)
        except ValueError:
            logging.error(f"Invalid block range: '{blockno}'. Please provide valid integers.")
    elif command == "rollback":
        rollback_files()
    elif command.startswith("rollback datafile") and len(command.split()) == 3:
        try:
            datafile_index = int(command.split()[2])
            rollback_files(datafile_index)
        except ValueError:
            logging.error("Invalid datafile number. Please provide a valid integer.")
    else:
        logging.error("Invalid recover command. Please use 'all', 'datafile N', or 'rollback'.")

