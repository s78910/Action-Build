@echo off
chcp 65001 >nul
title OnePlus 11 Android 16 内核刷入工具 (BakaSU + SuSFS)

echo ========================================================
echo        OnePlus 11 Android 16 一键刷入最新内核
echo ========================================================
echo 正在检测 Fastboot 模式连接设备...
fastboot devices

set TARGET_SERIAL=16730370
fastboot devices | findstr /i "%TARGET_SERIAL%" >nul
if %errorlevel% equ 0 (
    set FASTBOOT_CMD=fastboot -s %TARGET_SERIAL%
    echo [安全保护] 锁定目标一加 11 设备 (序列号: %TARGET_SERIAL%)，防止多机错刷
) else (
    set FASTBOOT_CMD=fastboot
    echo 默认使用 fastboot 单机模式
)

echo.
echo 准备将最新内核刷入一加 11 boot 分区: boot_oneplus11_a16_resukisu.img
echo 按任意键开始刷入，或直接关闭窗口取消...
pause >nul

echo 正在刷入 boot 分区...
%FASTBOOT_CMD% flash boot "%~dp0boot_oneplus11_a16_resukisu.img"
if %errorlevel% neq 0 (
    echo.
    echo [错误] 刷入失败！请检查 USB 连接和 Bootloader 解锁状态。
    pause
    exit /b 1
)

echo.
echo [成功] 内核刷入完成！
echo 正在重启设备进入系统...
%FASTBOOT_CMD% reboot

echo.
echo 开机后请打开桌面的 ReSukiSU 管理器赋予权限。
echo 全部操作已完成，按任意键退出。
pause >nul
