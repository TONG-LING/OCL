import os
import link  # 直接在函数内部引入 link

Controlfile_checkpoint_count = 0x600CC  # 偏移量基准


def read_file_offset(file_path, offset, size):
    """从文件特定偏移量读取数据"""
    try:
        with open(file_path, "rb") as f:
            f.seek(offset)
            return f.read(size)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return None


def find_file_fhcpc(file_path):
    """
    1. 传入文件路径，匹配 `link.db_files` 确定 `fno`
    2. 计算 `fno` 对应的 `Controlfile_checkpoint_count` 偏移量
    3. 读取 4 字节并直接转换为十进制返回
    """
    # 在 link.db_files 里查找匹配的 fno
    fno = None
    for db_file in link.db_files:
        if os.path.abspath(db_file.path) == os.path.abspath(file_path):
            fno = db_file.fno
            break

    if fno is None:
        print(f"Error: File {file_path} not found in link.db_files.")
        return None

    # 计算控制文件中的偏移量
    offset = Controlfile_checkpoint_count + (int(fno) - 1) * 520  # 确保 fno 是整数
    #print(link.control_file)
    #print(offset)
    # 读取偏移量数据
    data = read_file_offset(link.control_file, offset, 4)
    if data is None:
        return None

    #print(data)

    # 直接将读取到的字节数据转换为十进制并返回
    return (data)

