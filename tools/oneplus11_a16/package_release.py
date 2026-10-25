#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finalize release artifacts for OnePlus 11 Android 16
1. Repack stock boot.img with compiled Image
2. Zip AnyKernel3 directory
3. Copy Manager APK
4. Generate flash_resukisu.bat & restore_stock.bat with UTF-8 BOM
5. Generate checksums.txt
"""

import os
import sys
import shutil
import hashlib
import zipfile
import subprocess

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def make_zip(source_dir, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                zf.write(full_path, rel_path)

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    release_dir = os.path.join(base_dir, "release")
    stock_boot = os.path.join(base_dir, "stock", "boot.img")
    temp_art = os.path.join(release_dir, "temp_artifacts")
    ak3_folder = os.path.join(temp_art, "AnyKernel3_BakaSU_30750_OnePlus11_Android16.0.0(5.15.180)_KPN_ILH")

    if not os.path.exists(ak3_folder):
        print(f"[-] Error: AnyKernel3 folder not found at {ak3_folder}")
        return 1

    print("[*] 1. Creating AnyKernel3 zip package...")
    ak3_zip_name = "AnyKernel3_BakaSU_30750_OnePlus11_Android16.0.0(5.15.180)_KPN_ILH.zip"
    ak3_zip_path = os.path.join(release_dir, ak3_zip_name)
    make_zip(ak3_folder, ak3_zip_path)
    print(f"[+] AnyKernel3 zip created: {ak3_zip_path} ({os.path.getsize(ak3_zip_path):,} bytes)")

    print("[*] 2. Extracting Manager APK...")
    apk_source = os.path.join(ak3_folder, "BakaSU_v4.2.0-rc3_35234-arm64-v8a-release.apk")
    apk_dest = os.path.join(release_dir, "BakaSU_v4.2.0-rc3_Official_Manager.apk")
    if os.path.exists(apk_source):
        shutil.copyfile(apk_source, apk_dest)
        print(f"[+] Manager APK copied: {apk_dest} ({os.path.getsize(apk_dest):,} bytes)")

    print("[*] 3. Repacking boot.img with compiled Image...")
    compiled_image = os.path.join(ak3_folder, "Image")
    output_boot = os.path.join(release_dir, "boot_oneplus11_a16_resukisu.img")
    repack_script = os.path.join(base_dir, "tools", "repack_boot.py")
    res_repack = subprocess.run([sys.executable, repack_script, "-b", stock_boot, "-k", compiled_image, "-o", output_boot], capture_output=True, text=True)
    print(res_repack.stdout)
    if res_repack.returncode != 0:
        print(f"[-] Repack failed: {res_repack.stderr}")
        return 1

    print("[*] 4. Ensuring boot_stock.img exists in release...")
    stock_boot_release = os.path.join(release_dir, "boot_stock.img")
    if not os.path.exists(stock_boot_release):
        shutil.copyfile(stock_boot, stock_boot_release)

    print("[*] 5. Writing fastboot flash and restore batch scripts (UTF-8 BOM)...")
    flash_bat = os.path.join(release_dir, "flash_resukisu.bat")
    flash_bat_content = """@echo off
chcp 65001 >nul
title OnePlus 11 Android 16 内核刷入工具 (BakaSU + SuSFS)

echo ========================================================
echo        OnePlus 11 Android 16 一键刷入最新内核
echo ========================================================
echo 正在检测 Fastboot 模式连接设备...
fastboot devices

echo.
echo 准备将最新内核刷入 boot 分区: boot_oneplus11_a16_resukisu.img
echo 按任意键开始刷入，或直接关闭窗口取消...
pause >nul

echo 正在刷入 boot 分区...
fastboot flash boot "%~dp0boot_oneplus11_a16_resukisu.img"
if %errorlevel% neq 0 (
    echo.
    echo [错误] 刷入失败！请检查 USB 连接和 Bootloader 解锁状态。
    pause
    exit /b 1
)

echo.
echo [成功] 内核刷入完成！
echo 正在重启设备进入系统...
fastboot reboot

echo.
echo 开机后请安装并打开目录下的 BakaSU_v4.2.0-rc3_Official_Manager.apk 管理器赋予权限。
echo 全部操作已完成，按任意键退出。
pause >nul
"""
    with open(flash_bat, "w", encoding="utf-8-sig") as f:
        f.write(flash_bat_content)

    restore_bat = os.path.join(release_dir, "restore_stock.bat")
    restore_bat_content = """@echo off
chcp 65001 >nul
title OnePlus 11 Android 16 官方原厂内核还原工具

echo ========================================================
echo        OnePlus 11 Android 16 一键刷回官方原厂内核
echo ========================================================
echo 正在检测 Fastboot 模式连接设备...
fastboot devices

echo.
echo 准备将 100% 官方原厂纯净内核刷回 boot 分区...
echo 按任意键开始还原，或直接关闭窗口取消...
pause >nul

echo 正在还原官方 boot 分区...
fastboot flash boot "%~dp0boot_stock.img"
if %errorlevel% neq 0 (
    echo.
    echo [错误] 还原失败！请检查 Fastboot 连接。
    pause
    exit /b 1
)

echo.
echo [成功] 官方原厂内核已成功恢复！
echo 正在重启设备...
fastboot reboot

echo 全部操作已完成，设备已恢复官方出厂内核状态。
pause >nul
"""
    with open(restore_bat, "w", encoding="utf-8-sig") as f:
        f.write(restore_bat_content)

    print("[*] 6. Generating checksums.txt...")
    checksums_path = os.path.join(release_dir, "checksums.txt")
    files_to_hash = [
        "boot_oneplus11_a16_resukisu.img",
        "boot_stock.img",
        ak3_zip_name,
        "BakaSU_v4.2.0-rc3_Official_Manager.apk"
    ]
    with open(checksums_path, "w", encoding="utf-8") as f:
        for fname in files_to_hash:
            fpath = os.path.join(release_dir, fname)
            if os.path.exists(fpath):
                sha = compute_sha256(fpath)
                f.write(f"{sha}  {fname}\n")
                print(f"  {fname}: {sha}")

    print("[*] 7. Cleaning up temporary artifacts directory...")
    shutil.rmtree(temp_art, ignore_errors=True)

    print("\n=================================================================")
    print("[+] ALL RELEASE PACKAGING TASKS COMPLETED!")
    print(f"[+] Target release folder: {release_dir}")
    print("=================================================================")
    return 0

if __name__ == "__main__":
    sys.exit(main())
