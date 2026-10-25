import os
import subprocess
import sys
import time
import json

def get_env():
    env = os.environ.copy()
    env["HTTPS_PROXY"] = "http://127.0.0.1:7890"
    env["HTTP_PROXY"] = "http://127.0.0.1:7890"
    return env

def main():
    repo = "s78910/Action-Build"
    branch = "BakaSU"
    workflow = "Build Kernel OnePlus.yml"

    inputs = [
        ("FILE", "oneplus_11_b"),
        ("SUSFS_CI", "N/A"),
        ("KPM", "KPN"),
        ("SUSFS_META", ""),
        ("DYNAMIC_REPO", "Numbersf"),
        ("BUILD_TIME", "Thu Apr 2 08:08:53 UTC 2026"),
        ("KSU_META", "main/main//"),
        ("LZ4_UPDATE", "false"),
        ("ZRAM", "0/lz4kd/8589934592"),
        ("SUFFIX", "8-o-01178-gfc2079499f31"),
        ("RESUBLEVEL", ""),
        ("FAST_BUILD", "true"),
        ("LSM_BBG", "false"),
        ("NETFILTER", "false"),
        ("CCM", "false"),
        ("UNICODE_BYPASS", "true"),
        ("SCHED_HMBIRD", "false"),
        ("DROID_SPACES", "false"),
        ("RE_KERNEL", "false"),
        ("SUSFS_DEV", "false"),
        ("SPACE_NOCLEAN", "false"),
        ("BUILD_NOCACHE", "false"),
    ]

    cmd = ["gh", "workflow", "run", workflow, "--repo", repo, "--ref", branch]
    for k, v in inputs:
        cmd.extend(["-f", f"{k}={v}"])

    print(f"[*] Dispatching workflow '{workflow}' on {repo} ({branch})...")
    print(f"[*] Target device: OnePlus 11 (Android 16, config: oneplus_11_b)")
    print(f"[*] Kernel version: 5.15.180 (KMI: android13-5.15)")
    print(f"[*] Suffix: 8-o-01178-gfc2079499f31")
    print(f"[*] Build time: Thu Apr 2 08:08:53 UTC 2026")

    env = get_env()
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] Failed to trigger workflow: {res.stderr}")
        return 1

    print("[+] Workflow dispatched successfully!")
    print("[*] Waiting for workflow run to register...")
    time.sleep(6)

    # Fetch newest run
    res = subprocess.run(["gh", "run", "list", "--repo", repo, "--workflow", workflow, "-L", "1", "--json", "databaseId,url,status,createdAt,displayTitle"], env=env, capture_output=True, text=True)
    if res.returncode == 0:
        try:
            runs = json.loads(res.stdout)
            if runs:
                run = runs[0]
                print(f"[+] Active Run ID: {run['databaseId']}")
                print(f"[+] Run URL: {run['url']}")
                print(f"[+] Status: {run['status']}")
                print(f"[+] Title: {run['displayTitle']}")
        except Exception as e:
            print(f"[*] Raw run output: {res.stdout}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
