@echo off
chcp 65001 >nul
title OnePlus 11 Android 16 官方原厂内核还原工具

echo ========================================================
echo        OnePlus 11 Android 16 一键刷回官方原厂内核
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
echo 准备将 100% 官方原厂纯净内核刷回 boot 分区...
echo 按任意键开始还原，或直接关闭窗口取消...
pause >nul

echo 正在还原官方 boot 分区...
%FASTBOOT_CMD% flash boot "%~dp0boot_stock.img"
if %errorlevel% neq 0 (
    echo.
    echo [错误] 还原失败！请检查 Fastboot 连接。
    pause
    exit /b 1
)

echo.
echo [成功] 官方原厂内核已成功恢复！
echo 正在重启设备...
%FASTBOOT_CMD% reboot

echo 全部操作已完成，设备已恢复官方出厂内核状态。
pause >nul
