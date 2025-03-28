import os
import platform
import subprocess
import re
import pymem
import psutil

def pscn():
# 获取当前操作系统
    current_system = platform.system()
    # 判断是否为 Windows 系统
    if current_system == "Windows":
        print("The Window system has been detected")
        # 获取 TEMP 目录路径
        temp_dir = os.getenv('TEMP')  # 从环境变量中获取 TEMP
        if not temp_dir:
            print("TEMP PATH ERROR")
        else:
            #print(f"TEMP 目录为: {temp_dir}")

            # 定义 SQL 文件路径
            temp_file_path = os.path.join(temp_dir, "run_oracle.sql")

            # SQL 文件内容（左对齐）
            sql_content = (
                "conn / as sysdba\n"
                "oradebug setmypid\n"
                "spool run_oracle.spool\n"
                "oradebug DUMPvar SGA kcsgscn_\n"
                "spool off\n"
                "exit;\n"
                "exit;\n"
            )

            try:
                # 创建并写入 SQL 文件
                with open(temp_file_path, 'w') as file:
                    file.write(sql_content)
                #print(f"SQL 文件已创建并写入内容: {temp_file_path}")
            except Exception as e:
                print(f"An error occurred while writing to the file: {e}")

            # 搜索以 OracleService 开头的服务
            print("\nSearching for OracleService service...")
            try:
                # 使用 subprocess 调用 Windows 服务查询命令
                result = subprocess.run(
                    ["sc", "query"],
                    capture_output=True,
                    text=True,
                    shell=True
                )

                # 筛选出以 "OracleService" 开头的服务
                services = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip().startswith("SERVICE_NAME: OracleService")
                ]

                # 打印搜索结果
                if services:
                    print("Find the following OracleService services:")
                    service_names = [service.split(":")[1].strip() for service in services]
                    for service_name in service_names:
                        print(service_name)
                        # 根据找到的服务数量决定
                        if len(service_names) == 1:
                            chosen_service_name = service_names[0]
                            print(f"Automatically select the server process as:{chosen_service_name}")
                        else:
                            # 让用户选择服务
                            chosen_service_name = input("Please enter the service name to operate:")
                            # 确保用户输入的服务名在列表中
                            if chosen_service_name not in service_names:
                                print("Invalid service name entered.")
                                return
                        def get_service_executable_path(service_name):
                            """获取指定服务的可执行文件路径"""
                            try:
                                result = subprocess.run(
                                    ["sc", "qc", service_name],
                                    capture_output=True,
                                    text=True,
                                    shell=True
                                )
                                for line in result.stdout.splitlines():
                                    if "BINARY_PATH_NAME" in line:
                                        return line.split(":", 1)[1].strip()
                            except Exception as e:
                                print(f"Error trying to get path to service executable:{e}")
                            return None

                        # 获取服务的可执行文件路径
                        executable_path = get_service_executable_path(chosen_service_name)
                        if executable_path:
                            print(f"The executable path of {chosen_service_name} is {executable_path}")

                            # 提取 DBM 和路径
                            path_and_dbm = executable_path.split(" ")
                            if len(path_and_dbm) > 1:
                                full_oracle_path = " ".join(path_and_dbm[:-1])  # 提取完整路径
                                dbm_value = path_and_dbm[-1]  # 提取 DBM
                                #print(f"提取的路径为: {full_oracle_path}")
                                #print(f"提取的 DBM 为: {dbm_value}")
                                # 去除 \bin 及其后面的路径
                                oracle_home = os.path.dirname(full_oracle_path)  # 获取去除文件名后的路径
                                oracle_home = os.path.dirname(oracle_home)  # 再次去掉 \bin 目录
                                print(f"Set ORACLE_HOME to  {oracle_home}")

                                # 创建 BAT 文件内容（左对齐）
                                bat_file_content = (
                                    "cd " + temp_dir + "\n"
                                    "c:" + "\n"
                                    "set ORACLE_HOME=" + oracle_home + "\n"
                                    "set ORACLE_SID=" + dbm_value + "\n"
                                    + os.path.join(oracle_home, "bin", "sqlplus.exe") + " /nolog @run_oracle.sql\n"
                                    "exit\n"
                                )

                                # 定义 BAT 文件路径
                                bat_file_path = os.path.join(temp_dir, "run_oracle.bat")

                                # 写入 BAT 文件
                                with open(bat_file_path, 'w') as bat_file:
                                    bat_file.write(bat_file_content)
                                #print(f"BAT 文件已创建: {bat_file_path}")

                                def get_process_id_by_path(process_path):
                                    """根据进程路径获取进程ID"""
                                    for proc in psutil.process_iter(attrs=['pid', 'exe']):
                                        if proc.info['exe'] and proc.info['exe'].lower() == process_path.lower():
                                            return proc.info['pid']
                                    return None

                                # 执行 BAT 文件
                                subprocess.run([bat_file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                #print(f"已执行: {bat_file_path}")
                                spool_file_path = os.path.join(temp_dir, 'run_oracle.spool')
                                # 读取 spool 文件内容
                                try:
                                    with open(spool_file_path, 'r') as file:
                                        spool_content = file.read()

                                    # 使用正则表达式提取值
                                    match = re.search(r'\[(\w+),', spool_content)

                                    if match:
                                        memory_address_str = match.group(1)
                                        print(f"Extracted memory address:{memory_address_str}")

                                        try:
                                            # 转换为整数
                                            memory_address = int(memory_address_str, 16)
                                            #print(f"转换后的内存地址: {hex(memory_address)}")

                                            # 指定完整路径
                                            pid = get_process_id_by_path(full_oracle_path)

                                            if pid is not None:
                                                print(f"Find the process PID: {pid}")
                                                pm = pymem.Pymem(pid)

                                                # 读取内存
                                                value = pm.read_int(memory_address)
                                                print(f"Integer value of memory address {hex(memory_address)} : {value}")

                                                # 读取前四个字节
                                                bytes_value = pm.read_bytes(memory_address, 4)
                                                #print(f"内存地址 {hex(memory_address)} 的字节值: {bytes_value}")

                                                # 用户输入新的内存值
                                                new_value_input = input("Enter a new memory integer value (decimal):")

                                                if new_value_input:  # 检查输入是否为空
                                                    new_value = int(new_value_input)

                                                    # 判断 new_value 是否超过 2^32
                                                    if new_value >= 2 ** 32:
                                                        remainder = new_value % (2 ** 32)
                                                        quotient = new_value // (2 ** 32)

                                                        # 将余数写入指定内存地址
                                                        pm.write_int(memory_address, remainder)
                                                        # 将商写入后四个字节
                                                        pm.write_int(memory_address + 4, quotient)
                                                        print(
                                                            f"The value of the memory address {hex(memory_address)} has been updated to: {remainder}, the quotient into the last four bytes: {quotient}")
                                                    else:
                                                        # 直接存入
                                                        pm.write_int(memory_address, new_value)
                                                        print(f"The value of memory address {hex(memory_address)} has been updated to: {new_value}")

                                                else:
                                                    print("The memory value is not modified.")

                                        except Exception as e:
                                            print(f"Error reading memory: {e} ")
                                            print("Please execute this program as an Administrator!")
                                    else:
                                        print("No matching value was found")

                                except FileNotFoundError:
                                    print(f"Spool File not found")
                                except Exception as e:
                                    print(f"Error occurred: {e}")

                            else:
                                print(f"Unable to extract sid, path format is incorrect: {executable_path}")
                        else:
                            print(f"The path to the executable file for {chosen_service_name} could not be found.")
                else:
                    print("No OracleService service found.")
            except Exception as e:
                print(f"Error while searching for service: {e}")
    else:
        print(f"Other operating systems are not supported: {current_system}")

# if __name__ == "__main__":
#     pscn()