import link  # 导入整个 link 模块，而不是 `from link import db_files`

def info_command():
    """执行 info 命令，重新读取偏移量信息并打印表格"""

    link.update_db_files()  # 先更新 db_files，确保获取最新数据
    db_files = link.db_files  # 直接访问 link 模块里的最新 db_files

    if not db_files:
        print("[ERROR] No DB files found. Please run the 'link' command first.")
        return

    if not link.reference_file:
        print("[WARNING] No reference file.")
    else:
        print(f"Reference file: {link.reference_file}")
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
