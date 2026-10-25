#!/usr/bin/env python3
import os
import sys

def patch_selinux_hide():
    path = "KernelSU/kernel/feature/selinux_hide.c"
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "fake_state" in content:
        print("[+] selinux_hide.c already has fake_state")
        return
    
    decl = "\n#ifdef CONFIG_KSU_SUSFS\n#include <linux/version.h>\nstruct selinux_state fake_state;\n#endif\n"
    content = decl + content
    
    hook = "\n#ifdef CONFIG_KSU_SUSFS\n    fake_state.initialized = true;\n    fake_state.policy = backup_sepolicy;\n#endif\n"
    target = "void __init ksu_selinux_hide_init()\n{"
    if target in content:
        content = content.replace(target, target + hook)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Successfully patched fake_state into selinux_hide.c")

def patch_rules():
    path = "KernelSU/kernel/selinux/rules.c"
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "fake_state" in content:
        print("[+] rules.c already has fake_state sync")
        return
    
    target = "backup_sepolicy = ksu_dup_sepolicy(old_pol);"
    sync_code = "\n#ifdef CONFIG_KSU_SUSFS\n    {\n        extern struct selinux_state fake_state;\n        fake_state.initialized = true;\n        fake_state.policy = backup_sepolicy;\n    }\n#endif\n"
    if target in content:
        content = content.replace(target, target + sync_code)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Successfully patched fake_state sync into rules.c")

def patch_namespace():
    path = "common/fs/namespace.c"
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "susfs_def.h" in content:
        print("[+] namespace.c already has susfs_def.h")
        return
    
    snippet = "\n#ifdef CONFIG_KSU_SUSFS\n#include <linux/susfs_def.h>\n#endif\n#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT\nextern bool susfs_is_current_ksu_domain(void);\nextern struct static_key_true susfs_is_sdcard_android_data_not_decrypted;\n#define CL_COPY_MNT_NS BIT(25)\n#endif\n"
    target = '#include "pnode.h"'
    if target in content:
        content = content.replace(target, snippet + target)
    else:
        content = snippet + content
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Successfully patched susfs definitions into namespace.c")

if __name__ == "__main__":
    patch_selinux_hide()
    patch_rules()
    patch_namespace()
