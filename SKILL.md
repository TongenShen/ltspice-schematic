---
name: ltspice-schematic
description: "用代码生成 LTspice 原理图（.asc 文件）并自动验证。当用户要把文字或作业描述的电路（如 RC/RLC 滤波、分压、整流滤波、LED 驱动、三极管/MOS 开关与放大、555 振荡等）变成可在 LTspice 打开并仿真的原理图，或要求程序化、批量生成电路图时使用。做法：解析 LTspice 自带符号(.asy，打包在安装目录 lib.zip)的引脚坐标，按放置方向旋转/镜像，用 WIRE 连线生成 .asc，再用 LTspice -b 批处理仿真验证。不用于手工 GUI 拖拽，也不是只生成无原理图的 .cir 网表。"
---

## 概述

LTspice 的原理图 `.asc` 是纯文本。本 skill 用 `scripts/ltspice_builder.py` 解析 LTspice 符号（`.asy`，位于安装目录 `lib.zip` 内）的引脚坐标，按放置方向变换，再用 `WIRE` 连线生成可直接打开、可仿真的 `.asc`。

## 工作流

1. 复制 `scripts/example_rc.py` 为新脚本（与 `ltspice_builder.py` 同目录，直接 `import`）。
2. 建立对象：`lib = SymbolLib()`（自动定位 `lib.zip`）；`sch = Schematic()`。
3. 放元件：`s = sch.symbol(lib, name, x, y, orient, inst=, value=, windows=)`；用 `s.pins` 取各引脚的图纸绝对坐标。
4. 连线：`sch.wire(x1,y1,x2,y2)` 按引脚坐标连接；`sch.label`/`sch.ground` 放网络标签与地；`sch.spice_text(x,y,".tran 10m")` 加仿真指令。
5. 保存：`sch.save(path)` 生成 `.asc`。
6. 验证：运行 `LTspice.exe -b <file>.asc`（batch，批处理），读同名 `.log`，确认退出码 0、出现 `... succeeded`；必要时读生成的 `.net` 核对拓扑。
7. 用 LTspice 打开 `.asc` 供用户查看。

## 必须遵守的规则

- 不要手算引脚坐标：一律用 `symbol(...).pins`（已含旋转/镜像）。
- `WIRE` 端点必须与引脚坐标**完全相等**；坐标取 16 的倍数；两个引脚坐标重合即自动相连。
- 横放元件（`R90`/`R270`）默认文字会竖排并重叠：用 `windows=` 显式定位编号(窗口0)和数值(窗口3)，参照 `example_rc.py`。
- 子目录符号传相对名（如 `"Misc/xxx"`）；接地用 `sch.ground(x,y)`（即 `FLAG x y 0`），没有独立的 gnd 符号。
- 屏幕捕获可能与用户交互桌面**会话隔离**：启动的 LTspice 用户可见、agent 截图却拍不到。电路正确性以 `-b` 和 `.net` 为准，视觉布局请用户确认。
- 信号源取值（SINE/PULSE/PWL）、仿真指令（.op/.tran/.ac/.dc）与排错见 `references/asc_format.md`。

## 资源

- `scripts/ltspice_builder.py`：生成器库，提供 `Schematic`、`SymbolLib`，自动定位 LTspice 的 `lib.zip`。
- `scripts/example_rc.py`：RC 充电电路完整示例，可直接当模板（含 `windows=` 文字定位）。
- `references/asc_format.md`：`.asc`/`.asy` 语法、方向变换表、常用元件引脚速查、信号源与仿真指令、验证与排错；需要手写布局或排查问题时读取。
