#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OnePlus 11 Android 16 Build Watcher and Auto Packager
Monitors GitHub Actions run, downloads artifacts, and repacks boot.img.
"""

import os
import sys
import time
import json
import shutil
import hashlib
import subprocess

def get_env():
    env = os.environ.copy()
    env["HTTPS_PROXY"] = "http://127.0.0.1:7890"
    env["HTTP_PROXY"] = "http://127.0.0.1:7890"
    return env

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def generate_bat_scripts(release_dir, patched_boot_name):
    # Flash script (UTF-8 with BOM to prevent CMD garbled Chinese)
    flash_bat_content = f"""@echo off
chcp 65001 >nul
title OnePlus 11 Android 16 内核刷入工具 (BakaSU + SuSFS)

echo ========================================================
echo        OnePlus 11 Android 16 一键刷入最新内核
echo ========================================================
echo 正在检测 Fastboot 模式连接设备...
fastboot devices

echo.
echo 准备将最新内核刷入 boot 分区: {patched_boot_name}
echo 按任意键开始刷入，或直接关闭窗口取消...
pause >nul

echo 正在刷入 boot 分区...
fastboot flash boot "%~dp0{patched_boot_name}"
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
echo 开机后请打开桌面配套的 BakaSU / ReSukiSU 管理器赋予权限。
echo 全部操作已完成，按任意键退出。
pause >nul
"""
    flash_bat_path = os.path.join(release_dir, "flash_resukisu.bat")
    with open(flash_bat_path, "w", encoding="utf-8-sig") as f:
        f.write(flash_bat_content)

    # Restore script
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
    restore_bat_path = os.path.join(release_dir, "restore_stock.bat")
    with open(restore_bat_path, "w", encoding="utf-8-sig") as f:
        f.write(restore_bat_content)

def watch_run(run_id, repo="s78910/Action-Build"):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    release_dir = os.path.join(base_dir, "release")
    stock_dir = os.path.join(base_dir, "stock")
    stock_boot = os.path.join(stock_dir, "boot.img")
    os.makedirs(release_dir, exist_ok=True)

    print(f"[*] Monitoring GitHub Run {run_id} on {repo}...")
    env = get_env()

    last_step = ""
    while True:
        res = subprocess.run(["gh", "run", "view", str(run_id), "--repo", repo, "--json", "status,conclusion,jobs"], env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[!] Warning: Query run failed: {res.stderr.strip()}, retrying in 15s...")
            time.sleep(15)
            continue

        try:
            data = json.loads(res.stdout)
        except Exception:
            time.sleep(15)
            continue

        status = data.get("status")
        conclusion = data.get("conclusion")

        # Track steps
        for j in data.get("jobs", []):
            for s in j.get("steps", []):
                if s.get("status") == "in_progress":
                    current_step = s.get("name")
                    if current_step != last_step:
                        last_step = current_step
                        print(f"[*] Step in progress: {current_step}")
                    break

        if status == "completed":
            print(f"\n[+] Workflow finished with conclusion: {conclusion}")
            if conclusion != "success":
                print(f"[-] Workflow failed! Please inspect logs at https://github.com/{repo}/actions/runs/{run_id}")
                return 1
            break

        time.sleep(20)

    # Download artifacts
    print("[*] Downloading compilation artifacts...")
    download_dir = os.path.join(release_dir, "temp_artifacts")
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir, ignore_errors=True)
    os.makedirs(download_dir, exist_ok=True)

    res_dl = subprocess.run(["gh", "run", "download", str(run_id), "--repo", repo, "--dir", download_dir], env=env, capture_output=True, text=True)
    if res_dl.returncode != 0:
        print(f"[-] Artifact download failed: {res_dl.stderr}")
        return 1

    # Locate AnyKernel3 zip
    ak3_zip = None
    manager_apk = None
    for root, dirs, files in os.walk(download_dir):
        for f in files:
            full_path = os.path.join(root, f)
            if f.endswith(".zip") and "AnyKernel3" in f:
                ak3_zip = full_path
            elif f.endswith(".apk"):
                manager_apk = full_path

    if not ak3_zip:
        # Search for any zip
        for root, dirs, files in os.walk(download_dir):
            for f in files:
                if f.endswith(".zip"):
                    ak3_zip = os.path.join(root, f)
                    break

    if not ak3_zip:
        print("[-] Could not locate AnyKernel3 zip in downloaded artifacts.")
        return 1

    target_ak3_name = os.path.basename(ak3_zip)
    dest_ak3 = os.path.join(release_dir, target_ak3_name)
    shutil.copyfile(ak3_zip, dest_ak3)
    print(f"[+] AnyKernel3 zip saved to: {dest_ak3} ({os.path.getsize(dest_ak3):,} bytes)")

    if manager_apk:
        dest_apk = os.path.join(release_dir, os.path.basename(manager_apk))
        shutil.copyfile(manager_apk, dest_apk)
        print(f"[+] Manager APK saved to: {dest_apk}")

    # Copy stock boot.img to release for instant recovery
    if os.path.exists(stock_boot):
        dest_stock = os.path.join(release_dir, "boot_stock.img")
        if not os.path.exists(dest_stock) or os.path.getsize(dest_stock) != os.path.getsize(stock_boot):
            shutil.copyfile(stock_boot, dest_stock)
            print(f"[+] Stock boot.img backed up to: {dest_stock}")

    # Repack boot.img with new kernel
    print("[*] Repacking boot.img with compiled Image from AnyKernel3...")
    repack_script = os.path.join(base_dir, "tools", "repack_boot.py")
    patched_boot = os.path.join(release_dir, "boot_oneplus11_a16_resukisu.img")
    res_repack = subprocess.run([sys.executable, repack_script, "-b", stock_boot, "-z", dest_ak3, "-o", patched_boot], capture_output=True, text=True)
    print(res_repack.stdout)
    if res_repack.returncode != 0:
        print(f"[-] Repack failed: {res_repack.stderr}")
        return 1

    # Generate Flash Scripts
    print("[*] Generating flash and restore batch scripts (UTF-8 with BOM)...")
    generate_bat_scripts(release_dir, os.path.basename(patched_boot))

    # Generate Checksums
    print("[*] Generating checksums.txt...")
    checksum_file = os.path.join(release_dir, "checksums.txt")
    with open(checksum_file, "w", encoding="utf-8") as f:
        for fname in [os.path.basename(patched_boot), "boot_stock.img", target_ak3_name]:
            fpath = os.path.join(release_dir, fname)
            if os.path.exists(fpath):
                sha = compute_sha256(fpath)
                f.write(f"{sha}  {fname}\n")

    # Clean up temp
    shutil.rmtree(download_dir, ignore_errors=True)

    print("\n=================================================================")
    print("[+] ALL TASKS COMPLETED SUCCESSFULLY!")
    print(f"[+] Patched boot image: {patched_boot}")
    print(f"[+] Fastboot flash script: {os.path.join(release_dir, 'flash_resukisu.bat')}")
    print(f"[+] Fastboot restore script: {os.path.join(release_dir, 'restore_stock.bat')}")
    print("=================================================================")
    return 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
    else:
        run_id = 39148431449
    sys.exit(watch_run(run_id))
