"""
配图生成工具 - 使用Matplotlib生成几何图形、数轴和统计图
"""
import math
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # 无GUI后端
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

from app.core.config import get_settings
from app.core.logging import logger


class FigureGenerator:
    """配图生成器"""

    def __init__(self):
        from app.core.config import model_config

        self.settings = get_settings()
        self.config = model_config.get_figure_generation_config()
        self.dpi = self.config.get("dpi", 150)
        self.figsize = tuple(self.config.get("figsize", [6, 6]))
        self.save_format = self.config.get("save_format", "png")

        # 从配置获取图片存储路径
        self.figure_dir = Path(self.settings.figure_dir)
        self.figure_url_prefix = self.settings.figure_url_prefix

        # 中文字体支持：优先使用配置字体，回退到系统常见中文字体
        plt.rcParams["font.sans-serif"] = [
            self.config.get("font_family", "SimHei"),
            "WenQuanYi Zen Hei",
            "Noto Sans CJK SC",
            "Noto Serif CJK SC",
            "DejaVu Sans",
        ]
        plt.rcParams["axes.unicode_minus"] = False

        # 创建图片存储目录
        self.figure_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"配图生成器初始化 | 存储路径: {self.figure_dir.absolute()}")

    def generate(self, spec: Dict[str, Any]) -> Optional[str]:
        """
        根据配图规格生成图片

        Args:
            spec: 配图规格，形如 {"figure_type": "rectangle", "params": {...}}

        Returns:
            图片的访问URL，失败返回None
        """
        figure_type = spec.get("figure_type")
        params = spec.get("params", {})

        handlers = {
            "rectangle": self._draw_rectangle,
            "square": self._draw_square,
            "triangle": self._draw_triangle,
            "circle": self._draw_circle,
            "number_line": self._draw_number_line,
            "bar_chart": self._draw_bar_chart,
            "pie_chart": self._draw_pie_chart,
            "line_chart": self._draw_line_chart,
        }

        handler = handlers.get(figure_type)
        if handler is None:
            logger.warning(f"不支持的配图类型: {figure_type}")
            return None

        try:
            fig, ax = plt.subplots(figsize=self.figsize)
            handler(ax, params)
            url = self._save(fig)
            plt.close(fig)
            logger.info(f"配图生成成功 | 类型: {figure_type} | URL: {url}")
            return url
        except Exception as e:  # noqa: BLE001 - 配图失败不应阻断主流程
            logger.exception(f"配图生成失败 | 类型: {figure_type} | Error: {e}")
            plt.close("all")
            return None

    def _save(self, fig) -> str:
        """保存图片并返回访问URL"""
        filename = f"{uuid.uuid4().hex}.{self.save_format}"
        filepath = self.figure_dir / filename
        fig.savefig(
            filepath,
            dpi=self.dpi,
            format=self.save_format,
            bbox_inches="tight",
        )
        return f"{self.figure_url_prefix}/{filename}"

    # ==================== 几何图形 ====================
    def _draw_rectangle(self, ax, params: Dict[str, Any]):
        width = float(params.get("width", 5))
        height = float(params.get("height", 3))
        unit = params.get("unit", "cm")
        show_dimensions = params.get("show_dimensions", True)

        ax.add_patch(Rectangle((0, 0), width, height, fill=False, linewidth=2))
        if show_dimensions:
            ax.text(width / 2, -height * 0.1, f"{width}{unit}", ha="center", va="top")
            ax.text(-width * 0.05, height / 2, f"{height}{unit}", ha="right", va="center", rotation=90)
        self._set_geometry_axes(ax, width, height)

    def _draw_square(self, ax, params: Dict[str, Any]):
        side = float(params.get("side", params.get("width", 4)))
        self._draw_rectangle(ax, {**params, "width": side, "height": side})

    def _draw_triangle(self, ax, params: Dict[str, Any]):
        """支持指定底和高，或三个顶点坐标"""
        unit = params.get("unit", "cm")
        vertices = params.get("vertices")
        if vertices and len(vertices) == 3:
            pts = [(float(x), float(y)) for x, y in vertices]
        else:
            base = float(params.get("base", 6))
            height = float(params.get("height", 4))
            pts = [(0, 0), (base, 0), (base / 2, height)]

        ax.add_patch(Polygon(pts, closed=True, fill=False, linewidth=2))
        if params.get("show_dimensions", True) and not vertices:
            base = pts[1][0]
            height = pts[2][1]
            ax.text(base / 2, -height * 0.08, f"底={base}{unit}", ha="center", va="top")
            ax.plot([pts[2][0], pts[2][0]], [0, height], linestyle="--", color="gray", linewidth=1)
            ax.text(pts[2][0] + 0.2, height / 2, f"高={height}{unit}", ha="left", va="center")

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self._set_geometry_axes(ax, max(xs) - min(xs), max(ys) - min(ys), xmin=min(xs), ymin=min(ys))

    def _draw_circle(self, ax, params: Dict[str, Any]):
        radius = float(params.get("radius", 3))
        unit = params.get("unit", "cm")
        ax.add_patch(Circle((0, 0), radius, fill=False, linewidth=2))
        if params.get("show_dimensions", True):
            ax.plot([0, radius], [0, 0], color="red", linewidth=1.5)
            ax.text(radius / 2, 0.2, f"r={radius}{unit}", ha="center", va="bottom", color="red")
            ax.plot(0, 0, "ko", markersize=3)
        ax.set_xlim(-radius * 1.3, radius * 1.3)
        ax.set_ylim(-radius * 1.3, radius * 1.3)
        ax.set_aspect("equal")
        ax.axis("off")

    def _set_geometry_axes(self, ax, width, height, xmin=0, ymin=0):
        """设置几何图形坐标轴范围"""
        margin = max(width, height) * 0.2 + 1
        ax.set_xlim(xmin - margin, xmin + width + margin)
        ax.set_ylim(ymin - margin, ymin + height + margin)
        ax.set_aspect("equal")
        ax.axis("off")

    # ==================== 数轴 ====================
    def _draw_number_line(self, ax, params: Dict[str, Any]):
        start = float(params.get("start", 0))
        end = float(params.get("end", 10))
        step = float(params.get("step", 1))
        points = params.get("points", [])  # 需标记的点 [{"value": 3, "label": "A"}]

        ax.axhline(0, color="black", linewidth=1.5)
        # 箭头
        ax.annotate("", xy=(end + step, 0), xytext=(end, 0),
                    arrowprops=dict(arrowstyle="->", color="black"))

        tick = start
        while tick <= end + 1e-9:
            ax.plot([tick, tick], [-0.1, 0.1], color="black", linewidth=1)
            label = int(tick) if float(tick).is_integer() else tick
            ax.text(tick, -0.25, str(label), ha="center", va="top")
            tick += step

        for p in points:
            value = float(p.get("value", 0))
            label = p.get("label", "")
            ax.plot(value, 0, "o", color="red", markersize=8)
            if label:
                ax.text(value, 0.3, label, ha="center", va="bottom", color="red", fontsize=12)

        ax.set_xlim(start - step, end + 2 * step)
        ax.set_ylim(-1, 1)
        ax.axis("off")

    # ==================== 统计图 ====================
    def _draw_bar_chart(self, ax, params: Dict[str, Any]):
        labels = params.get("labels", [])
        values = [float(v) for v in params.get("values", [])]
        title = params.get("title", "")
        xlabel = params.get("xlabel", "")
        ylabel = params.get("ylabel", "")

        ax.bar(labels, values, color="#4C72B0")
        for i, v in enumerate(values):
            ax.text(i, v, str(int(v) if float(v).is_integer() else v),
                    ha="center", va="bottom")
        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

    def _draw_pie_chart(self, ax, params: Dict[str, Any]):
        labels = params.get("labels", [])
        values = [float(v) for v in params.get("values", [])]
        title = params.get("title", "")
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_aspect("equal")
        if title:
            ax.set_title(title)

    def _draw_line_chart(self, ax, params: Dict[str, Any]):
        """折线统计图。支持单条(values)或多条(series=[{"name","values"}])折线"""
        labels = params.get("labels", [])
        title = params.get("title", "")
        xlabel = params.get("xlabel", "")
        ylabel = params.get("ylabel", "")
        series = params.get("series")

        if series:
            for s in series:
                vals = [float(v) for v in s.get("values", [])]
                ax.plot(labels[: len(vals)], vals, marker="o", label=s.get("name", ""))
            ax.legend()
        else:
            values = [float(v) for v in params.get("values", [])]
            ax.plot(labels[: len(values)], values, marker="o", color="#4C72B0")
            for x, y in zip(labels, values):
                ax.text(x, y, str(int(y) if float(y).is_integer() else y),
                        ha="center", va="bottom")

        ax.grid(True, linestyle="--", alpha=0.4)
        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)


# 全局单例
_figure_generator: Optional[FigureGenerator] = None


def get_figure_generator() -> FigureGenerator:
    """获取配图生成器实例（单例）"""
    global _figure_generator
    if _figure_generator is None:
        _figure_generator = FigureGenerator()
    return _figure_generator
