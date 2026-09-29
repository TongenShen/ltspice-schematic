# -*- coding: utf-8 -*-
"""
example_rc.py
最小示例：RC 充电电路。
  5V 直流源 V1 经 R1=1k 给 C1=1uF 充电；
  时间常数 tau = R*C = 1ms，仿真 10ms 可看到电容电压充到 5V。

运行：
  python example_rc.py            # 生成 rc_charge.asc（默认在当前目录）
  python example_rc.py D:/out     # 也可指定输出目录
然后用 LTspice 打开生成的 .asc，或：
  LTspice.exe -b rc_charge.asc    # 批处理跑仿真，看同名 .log
"""

import os
import sys
from ltspice_builder import Schematic, SymbolLib

out_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

lib = SymbolLib()                 # 自动定位 lib.zip
sch = Schematic()

# V1：引脚 +(96,160) -(96,240)；编号/数值文字放圆圈左侧
v1 = sch.symbol(lib, "voltage", 96, 144, "R0", inst="V1", value="5",
                windows={0: (-24, 24, "Right", 2),
                         3: (-24, 88, "Right", 2)})

# R1：R90 横放，左端 B(208,160) 右端 A(288,160)；
#   "R1" 放电阻上方中点，"1k" 放下方中点（本地坐标经 R90 旋转到位）
r1 = sch.symbol(lib, "res", 304, 144, "R90", inst="R1", value="1k",
                windows={0: (-8, 56, "Center", 2),
                         3: (40, 56, "Center", 2)})

# C1：上端 A(288,160) 下端 B(288,224)；文字放电容右侧
c1 = sch.symbol(lib, "cap", 272, 160, "R0", inst="C1", value="1u",
                windows={0: (40, 8, "Left", 2),
                         3: (40, 56, "Left", 2)})

# 主回路：V1+ -> R1 左端；R1 右端 (288,160) 与 C1 上端重合，自动相连
sch.wire(96, 160, 208, 160)
# Vc 标签：从节点竖直向上引出
sch.wire(288, 160, 288, 112)
sch.label(288, 112, "Vc")
# 地：C1 下端、V1- 都汇到 y=256 的地轨
sch.wire(288, 224, 288, 256)
sch.wire(96, 240, 96, 256)
sch.wire(96, 256, 288, 256)
sch.ground(192, 256)

sch.spice_text(48, 320, ".tran 10m")
sch.comment(48, 356, "RC charge: tau = R*C = 1ms")

out = os.path.join(out_dir, "rc_charge.asc")
os.makedirs(out_dir, exist_ok=True)
sch.save(out)

print("written :", out)
print("lib.zip :", lib.lib_zip)
print("V1 pins :", v1.pins)
print("R1 pins :", r1.pins, "(顺序: A右端, B左端)")
print("C1 pins :", c1.pins)
