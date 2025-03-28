from struct import Struct

# 定义结构体
ushort = Struct("<H")  # 小端 2 字节
ulong = Struct("<Q")  # 小端 8 字节

# 块大小
BLOCK_SIZE = 8192  # Oracle 数据块大小


def calculate_checksum(file_name, block_no=1):
    """计算数据库文件指定块的校验和"""
    try:
        with open(file_name, "rb") as dbf:
            dbf.seek(BLOCK_SIZE * block_no)  # 定位到指定块

            # **读取前 16 字节**
            block = dbf.read(16)

            # **清除 16 偏移处的 2 字节校验码**
            block += b"\x00\x00"

            # **跳过 16-18 偏移量，继续读取剩余数据**
            dbf.seek(BLOCK_SIZE * block_no + 18)
            block += dbf.read(BLOCK_SIZE - 18)

        # **校验数据是否完整**
        if len(block) != BLOCK_SIZE:
            print(f"错误: 读取的块大小不匹配，期望 {BLOCK_SIZE} 字节，实际 {len(block)} 字节")
            return None

        # **计算校验和**
        checksum_value = 0
        for i in range(BLOCK_SIZE // 8):  # 以 8 字节为单位 XOR
            checksum_value ^= ulong.unpack(block[i * 8:i * 8 + 8])[0]

        # **压缩到 16-bit**
        checksum_value ^= (checksum_value >> 32)  # 64-bit → 32-bit
        checksum_value ^= (checksum_value >> 16)  # 32-bit → 16-bit
        final_checksum = ushort.unpack(ulong.pack(checksum_value)[:2])[0]

        return final_checksum

    except FileNotFoundError:
        print(f"错误: 文件 {file_name} 未找到")
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None