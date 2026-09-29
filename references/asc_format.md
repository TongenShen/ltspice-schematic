# LTspice `.asc` 格式参考

生成器 `scripts/ltspice_builder.py` 已封装大部分细节；本文件供手写/排错时查阅。

## 目录
1. [`.asc` 总体结构](#asc-总体结构)
2. [关键字](#关键字)
3. [方向变换表](#方向变换表)
4. [常用元件引脚本地坐标](#常用元件引脚本地坐标)
5. [信号源取值写法](#信号源取值写法)
6. [常用仿真指令](#常用仿真指令)
7. [验证与排错](#验证与排错)

## `.asc` 总体结构

```
Version 4
SHEET 1 880 680
WIRE <x1> <y1> <x2> <y2>          # 导线
FLAG <x> <y> <netname>            # 网络标签；netname=0 即 GND
SYMBOL <name> <x> <y> <orient>    # 元件实例
WINDOW <n> <dx> <dy> <just> <sz>  # （可选）覆盖该元件文字位置
SYMATTR InstName <ref>            # 编号，如 R1
SYMATTR Value <val>               # 数值/型号
TEXT <x> <y> <just> <sz> !<cmd>   # SPICE 指令（! 前缀）
```

行顺序不敏感；约定 WIRE/FLAG 在前，SYMBOL 块在后。坐标建议取 **16 的倍数**。

## 关键字

- `WIRE x1 y1 x2 y2`：水平或垂直导线。端点与某引脚坐标相同即建立连接；两个引脚坐标重合也会自动相连。
- `SYMBOL name x y orient`：放置符号。顶层符号写 `res`；子目录写相对路径如 `Misc/xxx`。`x y` 是符号原点。
- `WINDOW n dx dy just size`：覆盖符号的文字窗口，坐标为**本地坐标**，随 orient 一起旋转。
  - 窗口 `0` = InstName（编号），窗口 `3` = Value（数值）。
  - `just`：`Left/Right/Center/Top/Bottom`，加 `V` 前缀（如 `VLeft`）表示竖排文字。
- `SYMATTR key value`：元件属性，常用 `InstName`、`Value`；也可加 `SpiceModel` 等。
- `FLAG x y net`：网络标签（Label Net）。`net` 为 `0` 时显示为接地符号（倒三角）。
- `TEXT x y just size body`：图纸文字；`body` 以 `!` 开头表示要执行的 SPICE 指令，否则是注释。

## 方向变换表

本地坐标 `(dx,dy)` → 相对符号原点的图纸坐标。屏幕坐标 x 向右、y 向下，`R90` 为顺时针 90°。

| orient | 变换 | orient | 变换 |
|---|---|---|---|
| R0 | `( dx, dy)` | M0 | `(-dx, dy)` |
| R90 | `(-dy, dx)` | M90 | `(-dy,-dx)` |
| R180 | `(-dx,-dy)` | M180 | `( dx,-dy)` |
| R270 | `( dy,-dx)` | M270 | `( dy, dx)` |

`R*` 为旋转，`M*` 为先水平镜像再旋转。

## 常用元件引脚本地坐标

顺序即 SpiceOrder（SPICE 端口顺序）。生成器用 `SymbolLib().pins(name)` 直接解析，**优先用程序结果**，下表仅速查。

| 符号 name | 引脚（本地坐标 / 名称） |
|---|---|
| `voltage` | (0,16) + ; (0,96) − |
| `res` | (16,16) A ; (16,96) B |
| `cap` | (16,0) A ; (16,64) B |
| `ind` | (16,16) A ; (16,96) B |
| `diode` | (16,0) +(阳极) ; (16,64) −(阴极) |
| `LED` | (16,0) +(阳极) ; (16,64) −(阴极) |
| `npn` | (64,0) C ; (0,48) B ; (64,96) E |
| `pnp` | 同 npn 布局（极性相反） |

接地没有独立符号，用 `FLAG x y 0`。

## 信号源取值写法

`voltage` 的 `Value`（也可在元件属性里设置）：

- 直流：`5`（即 5V DC）
- 正弦：`SINE(0 1 1k)` = 偏置 0、幅度 1、频率 1kHz；完整 `SINE(Voff Vamp Freq Td Theta Phi)`
- 脉冲：`PULSE(0 5 0 1u 1u 5m 10m)` = 初值 0、峰值 5、延迟 0、上升/下降 1µs、脉宽 5ms、周期 10ms
- 分段线性：`PWL(0 0 1m 5 5m 5)` = 逐点 (时间, 电压)
- 指数：`EXP(0 5 1m 0.5m 4m 2m)`

## 常用仿真指令

用 `sch.spice_text(x,y,".tran 10m")` 生成（自动加 `!`）：

- `.op`：直流工作点
- `.tran 10m`：瞬态 0~10ms；`.tran 0 10m 2m 1u` = (Tstop Tstart Tmax步长)
- **`.tran 1u 2m 0 1u uic`**：固定步长 + 跳过工作点、用初始条件启动（**modifier 必须小写 `uic`**，大写 `UIC` 在 LTspice 24 会报 `Expected end of line here`）
- `.ac dec 50 10 1Meg`：交流扫描，每十倍频 50 点，10Hz~1MHz
- `.dc V1 0 5 0.1`：直流扫描 V1，0→5V，步长 0.1
- `.model D1N4148 D(RS=0.1 ...)`：自定义模型
- `.ic V(out)=0`：设置初始条件

## 验证与排错

批处理（无界面）跑仿真：

```
LTspice.exe -b <file>.asc
```

完成后读同名 `.log`：

- 成功标志：`Direct Newton iteration ... succeeded`、退出码 0，并生成 `.raw`。
- **理想无损 LC / 振荡回路**：`.ic` 必须配合 `.tran ... uic`，否则工作点求解给出错误初始电流，波形会在微秒级数值发散到数万伏（`I(L)` 恒定在 V/L 的假值）。验证时若 Vmax 达 kV 级即此问题。
- **读取 `.raw` 波形**：LTspice 24 的 raw 文本头是 **UTF-16LE（无 BOM）**，不是 ASCII；PyLTSpice(spicelib) 对 24.1.x 的 raw 会报 `no axis`。自行解析：用 `"Binary:".encode('utf-16-le')` 定位数据起点，跳过换行后按 `time=f8 + 其余=f4` 小端解析（点数为头部 `No. Points`）。
- 常见问题：
  - **节点浮空 / `floating node`**：该元件引脚没连上，核对引脚坐标与 WIRE 端点是否完全相等。
  - **文字竖排或重叠**：横放元件(R90/R270)用 `windows=` 显式定位编号和数值。
  - **缺少模型 / `Unknown subcircuit`**：元件 Value 引用了库里没有的型号；改用通用值或加 `.lib`/`.model`。
  - 网表 `.net` 是 LTspice 从 `.asc` 生成的文本，读它可核对最终连接关系。
