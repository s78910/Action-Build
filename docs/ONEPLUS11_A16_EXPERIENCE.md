# 一加 11 (OnePlus 11 / Android 16) 内核编译实战与全链路经验手册

> **分支说明**：本分支（`一加11-1020-A16`）专用于归档与沉淀 **OnePlus 11 (SM8550)** 在 **Android 16 (ColorOS 16)** 环境下，成功集成 **BakaSU (KernelSU 最新分支) + SuSFS v2.3.0 + KPN** 的全套云端构建工作流、避坑补丁、自动化重打包工具链与刷机验证经验。

---

## 一、 硬件与系统核心基线

| 属性维度 | 参数指标与技术规范 |
| :--- | :--- |
| **设备机型** | 一加 11 (OnePlus 11 / 代号 `salami` / `kalama`) |
| **处理器平台** | 高通第二代骁龙 8 移动平台 (Qualcomm Snapdragon 8 Gen 2 / `SM8550`) |
| **系统版本** | Android 16 预览版 / 测试版 (ColorOS 16，固件版本 `16.0.5.701`) |
| **底层架构规范** | Google Android 13+ GKI 2.0 (Generic Kernel Image) 规范，Boot Header Version **v4** |
| **分区职能分工** | `boot` 分区仅存放纯未压缩内核二进制文件 (`kernel` / `Image`，约 54MB)；`ramdisk` 存放于 `init_boot` 分区 |
| **官方原厂内核 Banner** | `Linux version 5.15.180-android13-8-o-01178-gfc2079499f31 (build-user@build-host) (Android (8508608, based on r450784e) clang version 14.0.7) #1 SMP PREEMPT Thu Apr 2 08:08:53 UTC 2026` |
| **集成技术栈** | **BakaSU** (v4.2.0-rc3 / 驱动版本代码 `35234`) + **SuSFS v2.3.0** + **KPN** 模块注入 + **Unicode 零宽字符防御** |

---

## 二、 云端 Action 编译成功参数组合（黄金基准）

在 GitHub Actions 运行编译时，经实机 100% 验证通过的完整配置项如下：

```yaml
FILE: oneplus_11_b
# 解释：从 OnePlusOSS/kernel_manifest 拉取 oneplus/sm8550 分支下的 oneplus_11_b.xml (Android 16 基准)

SUSFS_CI: 2.3.0
# 解释：拉取 SuSFS v2.3.0 官方稳定驱动补丁

KPM: KPN
# 解释：启用 KernelPatch Next (通过 kptools 静态打桩注入 kpimg)

KSU_META: main/main//35234
# 解释：锁定管理器与内置分支为 main，版本代码精确对齐 35234 (BakaSU v4.2.0-rc3)，彻底避免管理器弹版本不一致警告

BUILD_TIME: Thu Apr 2 08:08:53 UTC 2026
# 解释：严格匹配官方底包的原厂构建时间戳（可选，亦可通过 SuSFS 动态伪装）

SUFFIX: 8-o-01178-gfc2079499f31
# 解释：严格复刻原厂内核后缀版本标识（可选，亦可通过 SuSFS 动态伪装）

FAST_BUILD: true
# 解释：启用极速构建加速管道

UNICODE_BYPASS: true
# 解释：打入 Unicode 不可见控制字符绕过漏洞防护补丁

SCHED_HMBIRD: false
# 【极度重要避坑点】：必须设为 false！
# 经严密核实，一加风驰调度 (HMBIRD) 仅在 Linux 6.6+ (一加 13 / SM8750) 架构中存在专属补丁分支。
# 一加 11 (SM8550 / 5.15 内核) 若开启此项，因缺少分支必定导致 CI 报错退出 (exit 11)。

SPACE_NOCLEAN: false
BUILD_NOCACHE: false
LSM_BBG: false
NETFILTER: false
CCM: false
```

---

## 三、 关键技术攻坚与三大避坑修复复盘

在本项目推进过程中，经历了 3 次关键底层编译修复，相关代码已全部合入仓库核心逻辑：

### 1. 修复 SuSFS 2.3.0 在 5.15.180 源码上的头文件缺失（Commit `bbc97ed`）
- **故障现象**：在 `Build Kernel FAST` 步骤编译 `fs/proc/task_mmu.c` 和 `fs/namespace.c` 时中断：
  ```text
  error: implicit declaration of function 'SUSFS_IS_INODE_OPEN_REDIRECT' [-Werror,-Wimplicit-function-declaration]
  error: implicit declaration of function 'SUSFS_IS_INODE_SUS_MAP' [-Werror,-Wimplicit-function-declaration]
  ```
- **病灶分析**：原厂 `task_mmu.c` 中没有预置 `#include <trace/hooks/mm.h>` 钩子，导致 SuSFS 补丁在此处的注入点匹配失败产生 `.rej` 文件。函数体内的后续修改被强行应用，但文件头部未引入 `<linux/susfs_def.h>`，从而被 Clang 的 `-Werror` 严格编译拦截。
- **解决方案**：在 `scripts/PatchFakePatches.kts` 的 `applyPostPatchFixups()` 兜底管道中注入自动化探测逻辑：若检测到源码调用了 SuSFS 宏却未包含声明，自动在 include 区域注入 `#include <linux/susfs_def.h>` 与 extern 符号声明。

### 2. 绕过 `susfs_compat.mk` 的人工阻断机制（Commit `652393e`）
- **故障现象**：SuSFS 上游部分分支的 `susfs_compat.mk` 中设置了特定环境的阻断断言，阻止在某些修改过的内核树上编译。
- **解决方案**：在补丁处理阶段自动规避非法阻断，确保 v2.3.0 驱动在 5.15.180 树上顺利编译。

### 3. Git 浅克隆导致 KSU_VERSION 计算异常修复（Commit `5b755bb`）
- **故障现象**：由于 GitHub CI 默认使用 `fetch-depth: 1` 浅克隆，导致通过 git rev-list 统计 commit 数量生成驱动版本号时只能计算出固定默认值（如 10xxx 或 12xxx），无法生成与最新管理器匹配的 `35234`。
- **解决方案**：在 CI 中检出完整 Git 历史，并支持通过 `KSU_META` 自定义传入版本号强行固化，彻底根治版本号漂移。

---

## 四、 本地配套自动化工具链（位于 `tools/oneplus11_a16/`）

本分支内附全套本地配套工具：

1. **`trigger_build.py`**：本地一键通过 GitHub API 触发云端 Action 编译，无需手动登录网页配置。
2. **`watch_and_package.py`**：自动化监听云端构建流水线，构建完成后自动下载 AnyKernel3 产物并调用 magiskboot 重封装为可直接刷入的 `boot.img`。
3. **`repack_boot.py`**：基于 Google Boot v4 规范的专用解包与封装引擎，从 AnyKernel3 提取 `Image` 并合成至原厂底包结构的 boot 镜像中。
4. **`package_release.py`**：自动化生成校验码、整理交付目录。
5. **`flash_resukisu.bat`**：带 UTF-8 防乱码处理的双击一键刷入脚本（自动执行 `fastboot flash boot ... && fastboot reboot`）。
6. **`restore_stock.bat`**：原厂纯净 boot 一键刷回救砖脚本。

---

## 五、 真机验证成果

- **刷入产物**：`boot_oneplus11_a16_resukisu.img`
- **验证环境**：一加 11 (ColorOS 16.0.5.701) 真机
- **状态表现**：
  - 正常进入桌面，无卡米，无黑屏。
  - Wi-Fi 6、蓝牙 5.3、触控高刷、仿生马达振感、哈苏相机拍照录像全部 100% 正常。
  - 打开 BakaSU 管理器，显示版本 `v4.2.0-rc3 (35234)`，SuSFS 状态 `v2.3.0` 正常生效。
  - 支持通过 SuSFS 实现内核 `uname` 与 `/proc/version` 动态伪装克隆。
