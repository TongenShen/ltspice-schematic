# ltspice-schematic

用 Python 代码生成 LTspice 原理图（`.asc`），并配合 `LTspice -b` 批处理仿真自动验证。

这是一个供 AI Agent 使用的 Skill 目录：把文字或作业描述的电路需求（RC/RLC 滤波、分压、整流滤波、LED 驱动、三极管/MOS 开关与放大、555 振荡等）变成可直接在 LTspice 打开、可仿真的原理图文件。全程无需手工 GUI 拖拽。

## 它能做什么

- **代码即电路图**：`.asc` 本质是纯文本，由 `WIRE`/`SYMBOL`/`FLAG`/`TEXT` 描述整张图纸
- **自动解析引脚坐标**：读取 LTspice 安装目录 `lib.zip` 内的 `.asy` 符号定义，按放置方向（`R0`–`R270` + 镜像）旋转/镜像算出引脚绝对坐标，**不用手算**
- **完整可仿真**：支持网络标签、接地、SPICE 指令（`.tran`/`.ac`/`.op`/`.dc`）与常见信号源（SINE/PULSE/PWL/EXP）
- **验证闭环**：`LTspice.exe -b` 批处理跑通电路，读 `.log`/`.net`/`.raw` 确认拓扑与波形

## 目录结构

```
ltspice-schematic/
├── SKILL.md                    # Skill 定义：触发条件、工作流、必须遵守的规则
├── README.md                   # 本文件：给人看的入口说明
├── LICENSE                     # MIT 许可证
├── .gitignore                  # Python / LTspice 产物忽略规则
├── references/
│   └── asc_format.md           # .asc/.asy 语法、方向变换表、引脚速查、排错
└── scripts/
    ├── ltspice_builder.py      # 生成器库：Schematic / SymbolLib
    └── example_rc.py           # RC 充电完整示例，可直接当模板
```

## 环境要求

| 依赖 | 说明 |
|---|---|
| Python 3.8+ | 生成器仅用标准库，无第三方依赖 |
| LTspice 24.x | 新版符号库打包为安装目录下的 `lib.zip`，自动定位 |
| Windows | `lib.zip` 定位逻辑按 Windows 安装路径编写 |

> 注意：生成器只支持新版 LTspice（`lib.zip` 打包的符号库）。LTspice XVII 的符号是解压目录形式，不在支持范围内。

## 快速开始

```bash
cd scripts
python example_rc.py            # 生成 rc_charge.asc（当前目录）
python example_rc.py D:/out     # 或指定输出目录
```

LTspice 打开 `rc_charge.asc` 查看电路，或批处理验证：

```bash
"<你的 LTspice 安装目录>\LTspice.exe" -b rc_charge.asc
```

退出码 0 且 `.log` 出现 `... succeeded` 即验证通过。

示例电路：5V 直流源经 1kΩ 给 1µF 充电，时间常数 τ = RC = 1ms，`.tran 10m` 内电容电压充到 5V。

## 自己写一个电路

复制 `scripts/example_rc.py` 为新脚本（与 `ltspice_builder.py` 同目录即可直接 `import`），核心 API：

```python
from ltspice_builder import Schematic, SymbolLib

lib = SymbolLib()                    # 自动定位 LTspice 的 lib.zip
sch = Schematic()

# 放元件：名称、图纸坐标、方向、编号、数值；windows= 显式定位文字（横放元件必需）
v1 = sch.symbol(lib, "voltage", 96, 144, "R0", inst="V1", value="5")
r1 = sch.symbol(lib, "res", 304, 144, "R90", inst="R1", value="1k")

# 连线一律用 s.pins 给出的引脚绝对坐标，不要手算
sch.wire(*v1.pins[0], *r1.pins[1])
sch.ground(192, 256)                 # 接地 = FLAG x y 0
sch.spice_text(48, 320, ".tran 10m")
sch.save("my_circuit.asc")
```

## 核心规则

1. 引脚坐标一律取 `sch.symbol(...).pins`，**不要手算**
2. `WIRE` 端点必须与引脚坐标**完全相等**；坐标取 16 的倍数；两个引脚坐标重合即自动相连
3. 横放元件（`R90`/`R270`）默认文字会竖排重叠，用 `windows=` 显式定位编号（窗口 0）与数值（窗口 3）
4. 接地没有独立符号，用 `sch.ground(x, y)`
5. 正确性以 `-b` 退出码 + `.net` 网表为准；视觉布局请用户确认（agent 屏幕捕获可能与用户交互桌面隔离）

## 实战排错要点（实测踩过的坑）

- **理想无损 LC / 振荡回路必须加 `uic`**：`.tran 1u 2m 0 1u uic`。不加 `uic` 时 LTspice 先求直流工作点，初始电流错误，波形会在微秒级数值发散到数十万伏
- **LTspice 24 的 modifier 区分大小写**：`uic` 合法；`UIC` 大写会报 `Expected end of line here`
- **读 `.raw` 波形**：LTspice 24 的 raw 文本头是 UTF-16LE（无 BOM），PyLTSpice(spicelib) 对 24.1.x 不兼容；需按 UTF-16 定位 `Binary:` 再解析

详细语法与排错见 [`references/asc_format.md`](references/asc_format.md)。

## 工作原理

```mermaid
flowchart LR
    A[Python 脚本] --> B[SymbolLib 解析 lib.zip 内 .asy 引脚]
    B --> C[Schematic 按 orient 变换 + WIRE 连线]
    C --> D[.asc 原理图文件]
    D --> E[LTspice -b 批处理仿真]
    E --> F[.log / .net / .raw 验证]
```

## 适用与不适用

- ✅ 把文字/作业描述的电路变成可仿真的原理图
- ✅ 程序化、批量生成电路图
- ❌ 手工 GUI 拖拽编辑
- ❌ 只生成无原理图的 `.cir` 网表

## 启用方式

本目录目前放在桌面，任何 AI Agent 手动读取即可使用。若希望 Agent 在遇到画电路需求时**自动触发**，把整个文件夹复制到 Agent 的 skill 目录（如 `C:\Users\Tonge\Doubao\skills\ltspice-schematic`）。

## 许可证

[MIT](LICENSE)，Copyright (c) 2026 TongenShen
