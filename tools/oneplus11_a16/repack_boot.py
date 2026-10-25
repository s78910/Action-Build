#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OnePlus 11 (Android 16 / GKI Header v4) Boot Image Repack Tool
Based on magiskboot - Unpack, replace kernel Image, and repack.
"""

import os
import sys
import shutil
import subprocess
import argparse
import zipfile

def find_magiskboot():
    candidates = [
        r"H:\1\boot-patch-ak3\BootPatcher_Project\tools\magiskboot.exe",
        os.path.join(os.path.dirname(__file__), "magiskboot.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def extract_kernel_from_ak3(ak3_zip_path, extract_dir):
    """Extract Image from AnyKernel3 zip"""
    with zipfile.ZipFile(ak3_zip_path, 'r') as zf:
        for name in zf.namelist():
            if name in ['Image', 'kernel/Image', 'tools/Image']:
                out_path = os.path.join(extract_dir, "Image")
                with open(out_path, 'wb') as f_out, zf.open(name, 'r') as f_in:
                    f_out.write(f_in.read())
                return out_path
    return None

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    stock_boot_default = os.path.join(base_dir, "stock", "boot.img")
    release_dir = os.path.join(base_dir, "release")
    os.makedirs(release_dir, exist_ok=True)
    output_boot_default = os.path.join(release_dir, "boot_oneplus11_a16_resukisu.img")

    parser = argparse.ArgumentParser(description="Repack OnePlus 11 Android 16 Boot Image")
    parser.add_argument("-b", "--boot", default=stock_boot_default, help="Path to original boot.img")
    parser.add_argument("-k", "--kernel", default="", help="Path to new kernel Image file")
    parser.add_argument("-z", "--zip", default="", help="Path to AnyKernel3 zip archive containing Image")
    parser.add_argument("-o", "--output", default=output_boot_default, help="Path to output boot.img")
    args = parser.parse_args()

    magiskboot = find_magiskboot()
    if not magiskboot:
        print("[-] Error: magiskboot.exe not found.")
        return 1

    if not os.path.exists(args.boot):
        print(f"[-] Error: Original boot image not found at {args.boot}")
        return 1

    work_dir = os.path.join(base_dir, "tools", "temp_repack")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir, exist_ok=True)

    try:
        # Determine kernel Image source
        kernel_image_path = args.kernel
        if not kernel_image_path and args.zip:
            print(f"[*] Extracting Image from AnyKernel3 archive: {args.zip}")
            kernel_image_path = extract_kernel_from_ak3(args.zip, work_dir)
            if not kernel_image_path:
                print("[-] Error: Could not locate 'Image' inside AnyKernel3 archive.")
                return 1

        if not kernel_image_path or not os.path.exists(kernel_image_path):
            print(f"[-] Error: Target kernel Image not found at '{kernel_image_path}'")
            return 1

        print(f"[*] Unpacking original boot.img ({args.boot})...")
        res_unpack = subprocess.run([magiskboot, "unpack", os.path.abspath(args.boot)], cwd=work_dir, capture_output=True, text=True)
        if res_unpack.returncode != 0:
            print(f"[-] magiskboot unpack failed: {res_unpack.stderr}")
            return 1

        # Replace kernel
        target_kernel = os.path.join(work_dir, "kernel")
        print(f"[*] Replacing kernel with new Image ({os.path.getsize(kernel_image_path):,} bytes)...")
        shutil.copyfile(kernel_image_path, target_kernel)

        # Repack
        out_abs = os.path.abspath(args.output)
        print(f"[*] Repacking into {out_abs}...")
        res_repack = subprocess.run([magiskboot, "repack", os.path.abspath(args.boot), out_abs], cwd=work_dir, capture_output=True, text=True)
        if res_repack.returncode != 0:
            print(f"[-] magiskboot repack failed: {res_repack.stderr}")
            return 1

        if os.path.exists(out_abs):
            print(f"[+] Successfully generated patched boot image: {out_abs} ({os.path.getsize(out_abs):,} bytes)")
        else:
            print("[-] Repack completed but output file not found.")
            return 1

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return 0

if __name__ == "__main__":
    sys.exit(main())
