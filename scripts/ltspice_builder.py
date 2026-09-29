# -*- coding: utf-8 -*-
"""
ltspice_builder.py
用代码生成 LTspice 原理图 (.asc)。

原理：
  1. LTspice 的 .asc 原理图是纯文本，用 WIRE/SYMBOL/FLAG/TEXT 描述图纸；
  2. 每个元件的引脚坐标定义在符号文件 .asy 中；新版 LTspice(24.x) 把库打包在
     安装目录的 lib.zip 内（条目路径 lib/sym/<name>.asy）；
  3. 引脚坐标按放置方向(R0/R90/R180/R270，可加镜像 M)做旋转变换；
  4. 用 WIRE 把需要相连的引脚坐标连起来，保存后用 LTspice 打开即是完整电路图。
"""

import os
import re
import glob
import zipfile


def find_lib_zip():
    """自动定位 LTspice 的 lib.zip；找不到返回 None。"""
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local, r"Programs\ADI\LTspice\lib.zip"),
        r"C:\Program Files\ADI\LTspice\lib.zip",
        r"C:\Program Files\LTC\LTspiceXVII\lib.zip",
        os.path.join(os.environ.get("ProgramFiles", ""), r"ADI\LTspice\lib.zip"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    # 兜底：在 LOCALAPPDATA / Program Files 下浅层搜索
    for root in (local, os.environ.get("ProgramFiles", ""),
                 os.environ.get("ProgramFiles(x86)", "")):
        if not root:
            continue
        for hit in glob.glob(os.path.join(root, "**", "lib.zip"), recursive=True):
            if os.path.isfile(hit) and "LTspice" in hit:
                return hit
    return None


# 兼容旧引用；运行时实际以 find_lib_zip() 的结果为准
DEFAULT_LIB_ZIP = find_lib_zip()


def _transform(dx, dy, orient):
    """符号本地坐标 -> 图纸相对坐标。屏幕坐标：x 向右、y 向下；R90 为顺时针 90 度。"""
    o = orient.upper()
    table = {
        "R0":   ( dx,  dy),
        "R90":  (-dy,  dx),
        "R180": (-dx, -dy),
        "R270": ( dy, -dx),
        "M0":   (-dx,  dy),
        "M90":  (-dy, -dx),
        "M180": ( dx, -dy),
        "M270": ( dy,  dx),
    }
    if o not in table:
        raise ValueError("unknown orientation %r, use R0/R90/R180/R270 or M0..M270" % orient)
    return table[o]


class SymbolLib:
    """从 LTspice 的 lib.zip 读取并解析 .asy 符号的引脚坐标。"""

    def __init__(self, lib_zip=None):
        lib_zip = lib_zip or DEFAULT_LIB_ZIP or find_lib_zip()
        if not lib_zip or not os.path.isfile(lib_zip):
            raise FileNotFoundError(
                "LTspice lib.zip not found; pass lib_zip=<path> explicitly")
        self.lib_zip = lib_zip
        self._zf = zipfile.ZipFile(lib_zip)
        self._pins = {}

    def pins(self, symbol):
        """返回符号引脚的本地坐标列表，顺序即 SpiceOrder（SPICE 端口顺序）。

        顶层符号直接传名字，如 "res"、"voltage"；
        子目录符号传相对路径，如 "Misc/npn"。
        """
        if symbol not in self._pins:
            entry = "lib/sym/%s.asy" % symbol.replace("\\", "/")
            try:
                text = self._zf.read(entry).decode("utf-8", "ignore")
            except KeyError:
                raise KeyError("symbol %r not found (%s in %s)"
                               % (symbol, entry, self.lib_zip))
            pins = []
            for m in re.finditer(r"^PIN\s+(-?\d+)\s+(-?\d+)\s+\S+\s+\d+", text, re.M):
                pins.append((int(m.group(1)), int(m.group(2))))
            if not pins:
                raise ValueError("no PIN found in %s" % entry)
            self._pins[symbol] = pins
        return self._pins[symbol]


class Symbol:
    def __init__(self, lib, name, x, y, orient, inst, value, extra_attrs, windows):
        self.name = name
        self.x, self.y, self.orient = x, y, orient
        self.inst, self.value = inst, value
        self.extra_attrs = extra_attrs or {}
        # windows: {窗口号: (本地dx, 本地dy, 对齐justification, 字号size)}
        # 窗口 0 = InstName，窗口 3 = Value；坐标随元件一起旋转
        self.windows = windows or {}
        local = lib.pins(name)
        self.pins = [
            (x + tx, y + ty)
            for (tx, ty) in (_transform(px, py, orient) for px, py in local)
        ]

    def render(self):
        lines = ["SYMBOL %s %d %d %s" % (self.name, self.x, self.y, self.orient)]
        for n in sorted(self.windows):
            dx, dy, just, size = self.windows[n]
            lines.append("WINDOW %d %d %d %s %d" % (n, dx, dy, just, size))
        lines.append("SYMATTR InstName %s" % self.inst)
        if self.value is not None and self.value != "":
            lines.append("SYMATTR Value %s" % self.value)
        for k, v in self.extra_attrs.items():
            lines.append("SYMATTR %s %s" % (k, v))
        return lines


class Schematic:
    def __init__(self, sheet_w=880, sheet_h=680):
        self.sheet_w, self.sheet_h = sheet_w, sheet_h
        self._wires = []
        self._symbols = []
        self._flags = []
        self._texts = []

    def wire(self, x1, y1, x2, y2):
        """画一根导线（水平或垂直，端点建议取 16 的倍数并对准引脚）。"""
        self._wires.append((x1, y1, x2, y2))
        return (x1, y1, x2, y2)

    def symbol(self, lib, name, x, y, orient="R0", inst="", value="",
               windows=None, **attrs):
        """放置一个元件，返回 Symbol；symbol.pins 是各引脚在图纸上的绝对坐标。

        windows: {0:(dx,dy,just,size), 3:(...)} 自定义编号/数值文字位置，
                 坐标为符号本地坐标，会随 orient 一起旋转；
                 just 取 Left/Right/Center 等。
        """
        s = Symbol(lib, name, x, y, orient, inst, value, attrs, windows)
        self._symbols.append(s)
        return s

    def label(self, x, y, net):
        """放置网络标签（Label Net）；net='0' 时即接地 GND。"""
        self._flags.append((x, y, net))

    def ground(self, x, y):
        self._flags.append((x, y, "0"))

    def spice_text(self, x, y, cmd, align="Left", size=2):
        """放置一条 SPICE 指令（以 . 开头，如 .tran 10m）。"""
        self._texts.append((x, y, align, size, "!" + cmd))

    def comment(self, x, y, text, align="Left", size=2):
        """放置普通注释文字。"""
        self._texts.append((x, y, align, size, text))

    def render(self):
        out = ["Version 4", "SHEET 1 %d %d" % (self.sheet_w, self.sheet_h)]
        for w in self._wires:
            out.append("WIRE %d %d %d %d" % w)
        for f in self._flags:
            out.append("FLAG %d %d %s" % f)
        for s in self._symbols:
            out.extend(s.render())
        for (x, y, align, size, body) in self._texts:
            out.append("TEXT %d %d %s %d %s" % (x, y, align, size, body))
        out.append("")  # 文件末尾换行
        return "\r\n".join(out)

    def save(self, path):
        with open(path, "w", newline="") as f:
            f.write(self.render())
        return path
