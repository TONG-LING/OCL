#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

int main() {
    const char *outputFile = "full_output.txt";

    // 打开输出文件
    FILE *fout = fopen(outputFile, "w");
    if (fout == NULL) {
        perror("Failed to open output file");
        return 1;
    }

    // 创建管道
    SECURITY_ATTRIBUTES sa;
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = TRUE;
    sa.lpSecurityDescriptor = NULL;

    HANDLE hChildStdoutRd, hChildStdoutWr;
    if (!CreatePipe(&hChildStdoutRd, &hChildStdoutWr, &sa, 0)) {
        fprintf(stderr, "CreatePipe failed (%d).\n", GetLastError());
        fclose(fout);
        return 1;
    }

    // 设置进程启动信息
    STARTUPINFO si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));

    si.hStdError = hChildStdoutWr;
    si.hStdOutput = hChildStdoutWr;
    si.dwFlags |= STARTF_USESTDHANDLES;

    // 创建子进程
    if (!CreateProcess(
            NULL,           // 不指定可执行文件路径
            "sqlplus / as sysdba", // 命令
            NULL,           // 进程句柄不可继承
            NULL,           // 线程句柄不可继承
            TRUE,           // 继承句柄
            CREATE_NO_WINDOW, // 隐藏窗口
            NULL,           // 使用父进程环境变量
            NULL,           // 使用父进程工作目录
            &si,            // 启动信息
            &pi             // 进程信息
    )) {
        fprintf(stderr, "CreateProcess failed (%d).\n", GetLastError());
        fclose(fout);
        return 1;
    }

    // 关闭不必要的句柄
    CloseHandle(hChildStdoutWr);

    // 读取子进程的输出
    char buffer[1024];
    DWORD bytesRead;
    while (ReadFile(hChildStdoutRd, buffer, sizeof(buffer), &bytesRead, NULL) && bytesRead > 0) {
        // 将输出写入文件
        fwrite(buffer, 1, bytesRead, fout);

        // 打印到控制台（可选）
        fwrite(buffer, 1, bytesRead, stdout);
    }

    // 向子进程发送命令
    const char *commands =
            "oradebug setmypid\n"
            "oradebug dumpvar sga kcsgscn\n"
            "exit\n";

    HANDLE hChildStdinWr = GetStdHandle(STD_INPUT_HANDLE);
    WriteFile(hChildStdinWr, commands, strlen(commands), NULL, NULL);

    // 等待子进程结束
    WaitForSingleObject(pi.hProcess, INFINITE);

    // 关闭句柄
    CloseHandle(hChildStdoutRd);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);

    // 关闭输出文件
    fclose(fout);

    printf("Full output saved to '%s'.\n", outputFile);

    return 0;
}