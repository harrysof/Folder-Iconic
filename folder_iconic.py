"""Folder Iconic - build custom two-tone folder icons with layers.

The icon is a folder silhouette (traced from the user's existing .ico set)
plus an ordered stack of layers:
  * image layers  - your own PNG/JPG, with resolution cap, opacity, scale,
                    recolour and drop shadow
  * text layers   - any system or custom .ttf/.otf font, with opacity,
                    scale and drop shadow

Requires: Pillow, numpy (tkinter ships with Python).
Optional: rembg, used only by the "Remove background" button and installed
on demand the first time you click it.
"""

from __future__ import annotations

import colorsys
import ctypes
import glob
import math
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageTk

from svg_flattener import flatten_path

APP_NAME = "Folder Iconic"
APP_ID = "FolderIconic.App"
ICON_FILE = "Folder_Iconic.png"


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

# --------------------------------------------------------------------------
# Folder geometry on a 128x128 design canvas (traced from the icon set).
# --------------------------------------------------------------------------
DESIGN = 128
LEFT = 8
RIGHT = 120
BODY_TOP = 31
BODY_BOTTOM = 107
GLYPH_BOX_W = 0.62   # base glyph width  as a fraction of the body width
GLYPH_BOX_H = 0.78   # base glyph height as a fraction of the body height

DEFAULT_FRONT = "#008A00"
DEFAULT_BACK = "#88E588"

# resolution of the per-layer erase mask (covers the whole 128 design canvas)
MASK_RES = 256

ICO_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

ZOOM_MIN = 1.0
ZOOM_MAX = 12.0

OUTLINE_PATH = """
M 9.875 22.500 L 9.000 23.875 L 9.000 24.125 L 8.625 24.750 L 8.375 26.000 L 8.250 26.125 L 8.250 102.875 L 8.375 103.000 L 8.500 103.875 L 8.875 104.375 L 9.125 105.000 L 10.500 106.375 L 11.250 106.875 L 11.500 106.875 L 12.125 107.250 L 12.500 107.250 L 12.625 107.375 L 115.750 107.375 L 117.250 106.750 L 118.875 105.250 L 119.750 103.750 L 119.875 103.000 L 120.000 102.875 L 120.000 102.375 L 120.125 102.250 L 120.125 37.375 L 120.000 37.250 L 120.000 36.750 L 119.875 36.625 L 119.875 36.000 L 119.250 34.750 L 117.750 33.125 L 116.750 32.625 L 116.500 32.625 L 116.000 32.375 L 115.625 32.375 L 115.125 32.125 L 114.500 32.125 L 114.375 32.000 L 58.250 32.000 L 57.875 31.750 L 56.875 30.125 L 56.375 29.625 L 55.625 28.500 L 52.875 25.250 L 52.875 25.125 L 51.875 24.125 L 51.875 24.000 L 50.125 22.375 L 49.250 21.750 L 48.375 21.375 L 48.125 21.125 L 47.250 20.875 L 46.875 20.625 L 46.125 20.500 L 45.625 20.250 L 45.125 20.250 L 45.000 20.125 L 43.875 20.125 L 43.750 20.000 L 37.875 20.000 L 37.750 20.125 L 12.875 20.125 L 12.500 20.375 L 12.000 20.500 L 11.500 20.875 L 10.750 21.625 L 10.625 21.625 L 10.625 21.750 Z
"""
TAB_PATH = """
M 8.250 26.125 L 8.250 43.250 L 8.875 42.250 L 10.250 40.750 L 11.250 40.125 L 11.500 40.125 L 11.875 39.875 L 12.625 39.750 L 12.750 39.625 L 44.250 39.625 L 44.625 39.375 L 47.250 39.375 L 47.375 39.250 L 48.125 39.250 L 49.500 38.750 L 50.375 38.625 L 52.375 37.625 L 52.750 37.250 L 53.750 36.750 L 54.125 36.375 L 55.000 35.875 L 55.625 35.250 L 56.125 35.000 L 58.125 33.375 L 114.500 33.375 L 115.125 33.750 L 116.000 33.750 L 116.125 33.875 L 116.375 33.875 L 117.750 34.625 L 119.250 36.125 L 120.125 37.625 L 120.000 36.750 L 119.875 36.625 L 119.875 36.000 L 119.250 34.750 L 117.750 33.125 L 116.750 32.625 L 116.500 32.625 L 116.000 32.375 L 115.625 32.375 L 115.125 32.125 L 114.500 32.125 L 114.375 32.000 L 58.250 32.000 L 57.875 31.750 L 56.875 30.125 L 56.375 29.625 L 54.125 26.625 L 51.875 24.125 L 51.875 24.000 L 50.875 23.000 L 50.750 23.000 L 49.625 22.000 L 48.375 21.375 L 47.875 21.000 L 47.625 21.000 L 46.875 20.625 L 46.125 20.500 L 45.625 20.250 L 45.125 20.250 L 45.000 20.125 L 43.875 20.125 L 43.750 20.000 L 37.875 20.000 L 37.750 20.125 L 12.875 20.125 L 12.500 20.375 L 12.000 20.500 L 11.500 20.875 L 10.750 21.625 L 10.625 21.625 L 10.625 21.750 L 9.875 22.500 L 9.000 23.875 L 9.000 24.125 L 8.625 24.750 L 8.375 26.000 Z
"""
_OUTLINE_POINTS = flatten_path(OUTLINE_PATH)
_TAB_POINTS = flatten_path(TAB_PATH)

# centre of the folder body, where layers default to
BODY_CX = (LEFT + RIGHT) / 2.0
BODY_CY = (BODY_TOP + BODY_BOTTOM) / 2.0


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def clamp(value, low, high):
    return max(low, min(high, value))


def hex_to_rgb(text):
    text = str(text).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6:
        raise ValueError("expected 6 hex digits")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*[int(clamp(round(c), 0, 255)) for c in rgb])


def elide(text, limit=30):
    return text if len(text) <= limit else text[:limit - 1] + "\u2026"


def rgb_to_hsv01(rgb):
    return colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])


def hsv01_to_rgb(h, s, v):
    return tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h, s, v))


def hsv_to_rgb_array(h, s, v):
    h, s, v = np.broadcast_arrays(
        np.asarray(h, dtype=np.float64),
        np.asarray(s, dtype=np.float64),
        np.asarray(v, dtype=np.float64),
    )
    h = h % 1.0
    i = (np.floor(h * 6.0).astype(np.int64)) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    conds = [i == 0, i == 1, i == 2, i == 3, i == 4, i == 5]
    r = np.select(conds, [v, q, p, p, t, v])
    g = np.select(conds, [t, v, v, q, p, p])
    b = np.select(conds, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def make_hue_ring(size, thickness):
    c = size / 2.0
    radius = c - 2.0
    inner = radius - thickness
    yy, xx = np.mgrid[0:size, 0:size]
    dx = xx + 0.5 - c
    dy = yy + 0.5 - c
    dist = np.sqrt(dx * dx + dy * dy)
    angle = (np.degrees(np.arctan2(dy, dx)) + 360.0) % 360.0
    rgb = (np.clip(hsv_to_rgb_array(angle / 360.0, 1.0, 1.0), 0, 1) * 255).astype(np.uint8)
    edge = np.clip(np.minimum(dist - inner, radius - dist) + 0.5, 0.0, 1.0)
    alpha = (edge * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


def make_sv_square(side, hue):
    xs = np.linspace(0.0, 1.0, side)
    sat = np.tile(xs, (side, 1))
    val = np.tile(xs[::-1].reshape(-1, 1), (1, side))
    rgb = (np.clip(hsv_to_rgb_array(hue, sat, val), 0, 1) * 255).astype(np.uint8)
    alpha = np.full((side, side), 255, np.uint8)
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


_CHECKER_CACHE = {}


def make_checker(side, cell=16, c1="#3A3A3A", c2="#454545"):
    key = (side, cell, c1, c2)
    img = _CHECKER_CACHE.get(key)
    if img is not None:
        return img
    img = Image.new("RGB", (side, side), c1)
    draw = ImageDraw.Draw(img)
    for y in range(0, side, cell):
        for x in range(0, side, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=c2)
    img = img.convert("RGBA")
    _CHECKER_CACHE[key] = img
    return img


def make_eraser_icon(size=18):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([4, 9, 14, 15], radius=2,
                           fill="#F0A7B8", outline="#FFD4DE", width=1)
    draw.polygon([(8, 5), (15, 12), (12, 15), (5, 8)],
                 fill="#E8E8E8", outline="#FFFFFF")
    draw.line([(7, 10), (10, 7)], fill="#B7B7B7", width=1)
    draw.line([(3, 16), (15, 16)], fill="#686868", width=1)
    return img


def load_image(path):
    return Image.open(path).convert("RGBA")


def autocrop(img, pad_frac=0.02):
    img = img.convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        return img
    w, h = img.size
    pad = int(round(max(w, h) * pad_frac))
    x0, y0, x1, y1 = bbox
    return img.crop((max(0, x0 - pad), max(0, y0 - pad),
                     min(w, x1 + pad), min(h, y1 + pad)))


def recolor_solid(img, rgb):
    data = np.array(img.convert("RGBA"))
    data[..., 0] = rgb[0]
    data[..., 1] = rgb[1]
    data[..., 2] = rgb[2]
    return Image.fromarray(data, "RGBA")


def recolor_tint(img, rgb):
    data = np.array(img.convert("RGBA")).astype(np.float64)
    data[..., 0] *= rgb[0] / 255.0
    data[..., 1] *= rgb[1] / 255.0
    data[..., 2] *= rgb[2] / 255.0
    return Image.fromarray(np.clip(data, 0, 255).astype(np.uint8), "RGBA")


def apply_opacity(img, opacity):
    if opacity >= 1.0:
        return img
    alpha = img.getchannel("A").point(lambda v: int(v * opacity))
    img = img.copy()
    img.putalpha(alpha)
    return img


# --------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------
_FONT_CACHE = {}
_FONT_DIRS = [
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 "Microsoft", "Windows", "Fonts"),
]


def get_font(path, size):
    key = (path, size)
    font = _FONT_CACHE.get(key)
    if font is None:
        try:
            font = ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            font = ImageFont.load_default()
        if len(_FONT_CACHE) > 256:
            _FONT_CACHE.clear()
        _FONT_CACHE[key] = font
    return font


def font_label(path):
    try:
        family, style = ImageFont.truetype(path, 12).getname()
        return f"{family} {style}".strip()
    except Exception:  # noqa: BLE001
        return os.path.splitext(os.path.basename(path))[0]


def discover_fonts():
    fonts = {}
    for folder in _FONT_DIRS:
        if not folder or not os.path.isdir(folder):
            continue
        for pattern in ("*.ttf", "*.otf", "*.ttc"):
            for path in glob.glob(os.path.join(folder, pattern)):
                fonts[font_label(path)] = path
    return fonts


# --------------------------------------------------------------------------
# layers
# --------------------------------------------------------------------------
class Shadow:
    def __init__(self):
        self.enabled = False
        self.dx = 2.0
        self.dy = 2.0
        self.blur = 2.0
        self.opacity = 0.5
        self.color = (0, 0, 0)


class Layer:
    kind = "base"

    def __init__(self, name):
        self.name = name
        self.visible = True
        self.x = 0.0
        self.y = 0.0
        self.scale = 1.0
        self.opacity = 1.0
        self.color = (255, 255, 255)
        self.shadow = Shadow()
        self.erase_mask = None

    def render_tile(self, k):
        raise NotImplementedError

    def render(self, work, k):
        """Full-canvas composite (kept for convenience/tests)."""
        tile, pos = self.render_tile(k)
        canvas = Image.new("RGBA", (work, work), (0, 0, 0, 0))
        canvas.alpha_composite(tile, pos)
        return canvas

    def bbox_design(self):
        raise NotImplementedError

    # -- eraser -----------------------------------------------------------
    def ensure_mask(self):
        if self.erase_mask is None:
            self.erase_mask = Image.new("L", (MASK_RES, MASK_RES), 255)
        return self.erase_mask

    def erase_at(self, dx, dy, radius, restore=False, opacity=1.0):
        mask = self.ensure_mask()
        ms = MASK_RES / float(DESIGN)
        cx, cy, r = dx * ms, dy * ms, max(0.5, radius * ms)
        opacity = clamp(float(opacity), 0.0, 1.0)
        if opacity <= 0.0:
            return
        fill = 255 if restore else 0
        bounds = [cx - r, cy - r, cx + r, cy + r]
        if opacity >= 0.999:
            ImageDraw.Draw(mask).ellipse(bounds, fill=fill)
            return
        x0 = max(0, int(math.floor(bounds[0])))
        y0 = max(0, int(math.floor(bounds[1])))
        x1 = min(MASK_RES, int(math.ceil(bounds[2])))
        y1 = min(MASK_RES, int(math.ceil(bounds[3])))
        if x0 >= x1 or y0 >= y1:
            return
        box = (x0, y0, x1, y1)
        region = mask.crop(box)
        brush = Image.new("L", region.size, 0)
        ImageDraw.Draw(brush).ellipse(
            [bounds[0] - x0, bounds[1] - y0, bounds[2] - x0, bounds[3] - y0],
            fill=int(round(opacity * 255)))
        target = Image.new("L", region.size, fill)
        mask.paste(Image.composite(target, region, brush), box)

    def clear_mask(self):
        self.erase_mask = None

    def apply_erase(self, elem, pos, k):
        if self.erase_mask is None:
            return elem
        ms = MASK_RES / float(DESIGN)
        x0 = pos[0] / k
        y0 = pos[1] / k
        x1 = (pos[0] + elem.width) / k
        y1 = (pos[1] + elem.height) / k
        region = self.erase_mask.crop((x0 * ms, y0 * ms, x1 * ms, y1 * ms))
        region = region.resize(elem.size, Image.BILINEAR)
        elem = elem.copy()
        elem.putalpha(ImageChops.multiply(elem.getchannel("A"), region))
        return elem


def build_tile(elem, pos, shadow, k):
    """Composite one element (and its shadow) into a small tile.

    Returns (tile, top_left). Only the pixels the layer occupies are touched,
    instead of a full canvas-sized image per layer.
    """
    w, h = elem.size
    if shadow.enabled:
        pad = int(math.ceil((max(abs(shadow.dx), abs(shadow.dy))
                             + 3.0 * shadow.blur) * k)) + 2
    else:
        pad = 0
    tile = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if shadow.enabled:
        alpha = elem.getchannel("A")
        if shadow.blur > 0:
            alpha = alpha.filter(ImageFilter.GaussianBlur(shadow.blur * k))
        if shadow.opacity < 1.0:
            alpha = alpha.point(lambda v: int(v * shadow.opacity))
        sh = Image.new("RGBA", elem.size, tuple(shadow.color) + (0,))
        sh.putalpha(alpha)
        tile.alpha_composite(
            sh, (pad + int(round(shadow.dx * k)), pad + int(round(shadow.dy * k))))
    tile.alpha_composite(elem, (pad, pad))
    return tile, (int(round(pos[0])) - pad, int(round(pos[1])) - pad)


_BASE_CACHE = {}


def folder_base(work, k, front, back):
    """Folder silhouette, cached per (size, colours)."""
    key = (work, tuple(front), tuple(back))
    img = _BASE_CACHE.get(key)
    if img is None:
        img = Image.new("RGBA", (work, work), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.polygon([(x * k, y * k) for x, y in _OUTLINE_POINTS],
                     fill=tuple(front) + (255,))
        draw.polygon([(x * k, y * k) for x, y in _TAB_POINTS],
                     fill=tuple(back) + (255,))
        if len(_BASE_CACHE) > 6:
            _BASE_CACHE.clear()
        _BASE_CACHE[key] = img
    return img.copy()


class ImageLayer(Layer):
    kind = "image"

    def __init__(self, image, name):
        super().__init__(name)
        self.image = image.convert("RGBA")
        self.image_original = self.image
        self.source_res = 256
        self.recolor_mode = "original"
        self._prep_key = None
        self._prep_img = None

    def prepared(self):
        key = (id(self.image), self.source_res, self.recolor_mode, self.color)
        if key == self._prep_key and self._prep_img is not None:
            return self._prep_img
        img = self.image
        longest = max(img.size)
        if self.source_res and longest > self.source_res:
            r = self.source_res / longest
            img = img.resize((max(1, round(img.width * r)),
                              max(1, round(img.height * r))), Image.LANCZOS)
        if self.recolor_mode == "solid":
            img = recolor_solid(img, self.color)
        elif self.recolor_mode == "tint":
            img = recolor_tint(img, self.color)
        self._prep_key = key
        self._prep_img = img
        return img

    def _fit(self, img, k):
        box_w = (RIGHT - LEFT) * GLYPH_BOX_W * k
        box_h = (BODY_BOTTOM - BODY_TOP) * GLYPH_BOX_H * k
        fit = min(box_w / img.width, box_h / img.height)
        return max(1, round(img.width * fit * self.scale)), \
            max(1, round(img.height * fit * self.scale))

    def render_tile(self, k):
        img = self.prepared()
        tw, th = self._fit(img, k)
        img = img.resize((tw, th), Image.LANCZOS)
        img = apply_opacity(img, self.opacity)
        cx = BODY_CX * k + self.x * k
        cy = BODY_CY * k + self.y * k
        pos = (cx - tw / 2.0, cy - th / 2.0)
        img = self.apply_erase(img, pos, k)
        return build_tile(img, pos, self.shadow, k)

    def bbox_design(self):
        img = self.prepared()
        w, h = self._fit(img, 1.0)
        return (BODY_CX + self.x - w / 2.0, BODY_CY + self.y - h / 2.0,
                BODY_CX + self.x + w / 2.0, BODY_CY + self.y + h / 2.0)


class TextLayer(Layer):
    kind = "text"

    def __init__(self, text, font_path, name):
        super().__init__(name)
        self.text = text
        self.font_path = font_path
        self.font_size = 26.0
        self._txt_key = None
        self._txt_img = None

    def _render_text(self, k):
        key = (round(k, 4), self.text, self.font_path, self.font_size,
               self.scale, self.color)
        if key == self._txt_key and self._txt_img is not None:
            return self._txt_img
        size = max(4, int(round(self.font_size * k * self.scale)))
        font = get_font(self.font_path, size)
        spacing = max(1, int(size * 0.18))
        text = self.text if self.text else " "
        probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = probe.multiline_textbbox((0, 0), text, font=font,
                                        spacing=spacing, align="center")
        w = max(1, bbox[2] - bbox[0])
        h = max(1, bbox[3] - bbox[1])
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(img).multiline_text(
            (-bbox[0], -bbox[1]), text, font=font,
            fill=tuple(self.color) + (255,), spacing=spacing, align="center")
        self._txt_key = key
        self._txt_img = img
        return img

    def render_tile(self, k):
        img = apply_opacity(self._render_text(k), self.opacity)
        w, h = img.size
        cx = BODY_CX * k + self.x * k
        cy = BODY_CY * k + self.y * k
        pos = (cx - w / 2.0, cy - h / 2.0)
        img = self.apply_erase(img, pos, k)
        return build_tile(img, pos, self.shadow, k)

    def bbox_design(self):
        w, h = self._render_text(1.0).size
        return (BODY_CX + self.x - w / 2.0, BODY_CY + self.y - h / 2.0,
                BODY_CX + self.x + w / 2.0, BODY_CY + self.y + h / 2.0)


def render_document(size, ss, front, back, layers):
    work = size * ss
    k = work / DESIGN
    img = folder_base(work, k, front, back)
    for layer in layers:
        if layer.visible:
            tile, pos = layer.render_tile(k)
            img.alpha_composite(tile, pos)
    if ss != 1:
        return img.resize((size, size), Image.LANCZOS)
    return img


# --------------------------------------------------------------------------
# widgets
# --------------------------------------------------------------------------
class ColorWheel(tk.Canvas):
    def __init__(self, master, size=190, thickness=22, command=None):
        super().__init__(master, width=size, height=size, bd=0,
                         highlightthickness=0, bg="#2B2B2B")
        self.size = size
        self.radius = size / 2.0 - 2
        self.inner = self.radius - thickness
        self.command = command
        self.hue, self.sat, self.val = 0.0, 1.0, 1.0
        self._dragging = None

        self._ring_photo = ImageTk.PhotoImage(make_hue_ring(size, thickness))
        self.create_image(0, 0, anchor="nw", image=self._ring_photo)

        self._sq_side = int(self.inner * 1.35)
        self._sq_off = (size - self._sq_side) / 2.0
        self._sq_photo = None
        self._sq_item = None
        self._draw_square()

        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw_square(self):
        self._sq_photo = ImageTk.PhotoImage(make_sv_square(self._sq_side, self.hue))
        if self._sq_item is not None:
            self.delete(self._sq_item)
        self._sq_item = self.create_image(
            self._sq_off, self._sq_off, anchor="nw", image=self._sq_photo)
        self._draw_markers()

    def _draw_markers(self):
        self.delete("marker")
        cx = cy = self.size / 2.0
        ang = math.radians(self.hue * 360.0)
        mr = (self.radius + self.inner) / 2.0
        hx = cx + mr * math.cos(ang)
        hy = cy + mr * math.sin(ang)
        self.create_oval(hx - 6, hy - 6, hx + 6, hy + 6, outline="#FFFFFF",
                         width=2, tags="marker")
        self.create_oval(hx - 4, hy - 4, hx + 4, hy + 4, outline="#000000",
                         width=1, tags="marker")
        sx = self._sq_off + self.sat * (self._sq_side - 1)
        sy = self._sq_off + (1.0 - self.val) * (self._sq_side - 1)
        self.create_oval(sx - 6, sy - 6, sx + 6, sy + 6, outline="#FFFFFF",
                         width=2, tags="marker")
        self.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, outline="#000000",
                         width=1, tags="marker")

    def get_rgb(self):
        return hsv01_to_rgb(self.hue, self.sat, self.val)

    def set_rgb(self, rgb, fire=True):
        self.hue, self.sat, self.val = rgb_to_hsv01(rgb)
        self._draw_square()
        if fire:
            self._fire()

    def _fire(self):
        if self.command:
            self.command(self.get_rgb())

    def _in_square(self, x, y):
        return (self._sq_off <= x <= self._sq_off + self._sq_side and
                self._sq_off <= y <= self._sq_off + self._sq_side)

    def _on_press(self, event):
        if self._in_square(event.x, event.y):
            self._dragging = "sv"
        else:
            cx = cy = self.size / 2.0
            dist = math.hypot(event.x - cx, event.y - cy)
            if self.inner - 6 <= dist <= self.radius + 6:
                self._dragging = "hue"
            else:
                self._dragging = None
                return
        self._on_drag(event)

    def _on_drag(self, event):
        if self._dragging == "sv":
            self.sat = clamp((event.x - self._sq_off) / (self._sq_side - 1), 0, 1)
            self.val = clamp(1.0 - (event.y - self._sq_off) / (self._sq_side - 1), 0, 1)
            self._draw_markers()
            self._fire()
        elif self._dragging == "hue":
            cx = cy = self.size / 2.0
            ang = math.degrees(math.atan2(event.y - cy, event.x - cx))
            self.hue = (ang % 360.0) / 360.0
            self._draw_square()
            self._fire()

    def _on_release(self, _event):
        self._dragging = None


class Swatch(tk.Canvas):
    def __init__(self, master, rgb, on_click=None):
        super().__init__(master, width=58, height=34, bd=0,
                         highlightthickness=0, bg="#2B2B2B", cursor="hand2")
        self.rgb = rgb
        self.on_click = on_click
        self.active = False
        self.enabled = True
        self.bind("<Button-1>", self._clicked)
        self._render()

    def _clicked(self, _event):
        if self.enabled and self.on_click:
            self.on_click()

    def _render(self):
        self.delete("all")
        border = "#FFFFFF" if self.active else "#555555"
        fill = self.rgb
        if not self.enabled:
            fill = tuple(int(c * 0.45 + 0x2B * 0.55) for c in self.rgb)
            border = "#3A3A3A"
        self.create_rectangle(1, 1, 56, 32, outline=border,
                              width=3 if self.active else 1,
                              fill=rgb_to_hex(fill))

    def set_color(self, rgb):
        self.rgb = rgb
        self._render()

    def set_active(self, active):
        self.active = active
        self._render()

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            self.active = False
        self._render()


# --------------------------------------------------------------------------
# main application
# --------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg="#2B2B2B")
        self.minsize(1180, 640)
        self._set_window_icon()

        self.colors = {
            "front": hex_to_rgb(DEFAULT_FRONT),
            "back": hex_to_rgb(DEFAULT_BACK),
        }
        self.active = "front"
        self.layers = []
        self.selected = None
        self.fonts = {}
        self._font_ready = False
        self.default_font = None

        self.view_zoom = 2.6
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._drag = None
        self._last_paint = None
        self._cursor_pos = None
        self._icon_origin = (0.0, 0.0)
        self._preview_photo = None
        self._preview_icon = None
        self._preview_icon_key = None
        self._preview_icon_dirty = True
        self._render_job = None
        self._full_job = None
        self._fast = False
        self._checker_cache = {}
        self._bg_model = tk.StringVar(value="u2net")
        self._sessions = {}
        self._results = queue.Queue()

        self._make_vars()
        self._build_style()
        self._build_layout()
        self._select_target("front")
        self._refresh_layers()
        self._schedule_preview()
        self.after(300, self._start_font_scan)
        self.after(100, self._poll_results)

    def _start_font_scan(self):
        threading.Thread(target=self._load_fonts, daemon=True).start()

    def _set_window_icon(self):
        path = resource_path(ICON_FILE)
        if not os.path.exists(path):
            return
        try:
            image = Image.open(path).convert("RGBA")
        except OSError:
            return
        photos = []
        for size in (256, 128, 64, 48, 32, 16):
            photos.append(ImageTk.PhotoImage(image.resize((size, size),
                                                         Image.LANCZOS)))
        self._icon_photos = photos
        try:
            self.iconphoto(True, *photos)
        except tk.TclError:
            pass

    # -- worker -> main-thread handoff ------------------------------------
    def _poll_results(self):
        try:
            while True:
                self._results.get_nowait()()
        except queue.Empty:
            pass
        self.after(100, self._poll_results)

    # -- variables --------------------------------------------------------
    def _make_vars(self):
        self.var_name = tk.StringVar(value="")
        self.var_visible = tk.BooleanVar(value=True)
        self.var_x = tk.DoubleVar(value=0.0)
        self.var_y = tk.DoubleVar(value=0.0)
        self.var_scale = tk.DoubleVar(value=1.0)
        self.var_opacity = tk.DoubleVar(value=1.0)
        self.var_res = tk.DoubleVar(value=256.0)
        self.var_recolor = tk.StringVar(value="original")
        self.var_text = tk.StringVar(value="")
        self.var_font = tk.StringVar(value="")
        self.var_fontsize = tk.DoubleVar(value=26.0)
        self.var_shadow = tk.BooleanVar(value=False)
        self.var_sdx = tk.DoubleVar(value=2.0)
        self.var_sdy = tk.DoubleVar(value=2.0)
        self.var_sblur = tk.DoubleVar(value=2.0)
        self.var_sopacity = tk.DoubleVar(value=0.5)
        self.var_hex = tk.StringVar(value="")
        self.var_zoom = tk.DoubleVar(value=self.view_zoom)
        self.var_filename = tk.StringVar(value="My Folder")
        self.var_tool = tk.StringVar(value="move")
        self.var_brush = tk.DoubleVar(value=6.0)
        self.var_eraser_opacity = tk.DoubleVar(value=1.0)
        self._loading = False

    # -- styling ----------------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#2B2B2B")
        style.configure("TLabel", background="#2B2B2B", foreground="#E6E6E6")
        style.configure("Hint.TLabel", foreground="#9A9A9A")
        style.configure("TRadiobutton", background="#2B2B2B", foreground="#E6E6E6")
        style.configure("TCheckbutton", background="#2B2B2B", foreground="#E6E6E6")
        style.configure("TButton", padding=5)
        style.configure("Accent.TButton", padding=7)
        style.configure("TLabelframe", background="#2B2B2B",
                        bordercolor="#5A5A5A", relief="solid")
        style.configure("TLabelframe.Label", background="#2B2B2B",
                        foreground="#FFFFFF", font=("Segoe UI", 10, "bold"))
        style.configure("TSeparator", background="#5A5A5A")
        style.configure("TCombobox", padding=2)

    # -- layout -----------------------------------------------------------
    def _build_layout(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=0)
        root.columnconfigure(2, weight=1)
        root.rowconfigure(0, weight=1)

        self._build_preview(root)
        self._build_layers(root)
        self._build_right(root)

        self.status = ttk.Label(self, text="Ready.", style="Hint.TLabel", anchor="w")
        self.status.pack(fill="x", side="bottom", padx=10, pady=(0, 6))

    def _build_preview(self, parent):
        frame = ttk.LabelFrame(parent, text=" Preview ", padding=10)
        frame.grid(row=0, column=0, sticky="n")

        self.preview = tk.Canvas(frame, width=420, height=420, bd=0,
                                 highlightthickness=0, bg="#2B2B2B",
                                 cursor="fleur")
        self.preview.pack()
        self.preview.bind("<Button-1>", self._preview_press)
        self.preview.bind("<B1-Motion>", self._preview_motion)
        self.preview.bind("<ButtonRelease-1>", self._preview_release)
        self.preview.bind("<Button-3>", self._pan_press)
        self.preview.bind("<B3-Motion>", self._pan_motion)
        self.preview.bind("<Motion>", self._preview_hover)
        self.preview.bind("<Leave>", self._preview_leave)
        self.preview.bind("<MouseWheel>", self._wheel)
        self.preview.bind("<Button-4>", self._wheel)
        self.preview.bind("<Button-5>", self._wheel)

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Zoom").pack(side="left")
        ttk.Scale(row, from_=ZOOM_MIN, to=ZOOM_MAX, variable=self.var_zoom,
                  command=self._on_zoom).pack(side="left", fill="x",
                                              expand=True, padx=6)
        ttk.Button(row, text="Fit", width=5,
                   command=self._fit_view).pack(side="left")

        tools = ttk.Frame(frame)
        tools.pack(fill="x", pady=(8, 0))
        ttk.Label(tools, text="Tool:").pack(side="left")
        self._eraser_cursor = ImageTk.PhotoImage(make_eraser_icon(24))
        ttk.Radiobutton(tools, text="Move", value="move",
                        variable=self.var_tool,
                        command=self._on_tool).pack(side="left", padx=(4, 0))
        ttk.Radiobutton(tools, text="Erase", value="erase",
                        variable=self.var_tool,
                        command=self._on_tool).pack(side="left", padx=(4, 0))
        ttk.Radiobutton(tools, text="Restore", value="restore",
                        variable=self.var_tool,
                        command=self._on_tool).pack(side="left", padx=(4, 0))

        brow = ttk.Frame(frame)
        brow.pack(fill="x", pady=(4, 0))
        ttk.Label(brow, text="Brush").pack(side="left")
        ttk.Scale(brow, from_=1, to=30, variable=self.var_brush,
                  command=lambda v: self.brush_label.config(
                      text=f"{float(v):.0f}")).pack(side="left", fill="x",
                                                    expand=True, padx=6)
        self.brush_label = ttk.Label(brow, text="6", style="Hint.TLabel", width=3)
        self.brush_label.pack(side="left")
        ttk.Button(brow, text="Clear eraser",
                   command=self._clear_eraser).pack(side="left", padx=6)

        orow = ttk.Frame(frame)
        orow.pack(fill="x", pady=(4, 0))
        ttk.Label(orow, text="Opacity").pack(side="left")
        ttk.Scale(orow, from_=0.05, to=1.0, variable=self.var_eraser_opacity,
                  command=lambda v: self.eraser_opacity_label.config(
                      text=f"{float(v) * 100:.0f}%")).pack(side="left",
                                                           fill="x",
                                                           expand=True,
                                                           padx=6)
        self.eraser_opacity_label = ttk.Label(orow, text="100%",
                                              style="Hint.TLabel", width=4)
        self.eraser_opacity_label.pack(side="left")

        self.tool_hint = ttk.Label(frame, text="", style="Hint.TLabel",
                                   wraplength=400)
        self.tool_hint.pack(anchor="w", pady=(6, 0))
        self._on_tool()

    def _build_layers(self, parent):
        frame = ttk.LabelFrame(parent, text=" Layers ", padding=10)
        frame.grid(row=0, column=1, sticky="n", padx=(14, 0))

        self.layer_list = tk.Listbox(frame, width=26, height=12, bd=0,
                                     highlightthickness=1, activestyle="none",
                                     bg="#333333", fg="#E6E6E6",
                                     selectbackground="#0078D7",
                                     selectforeground="#FFFFFF",
                                     highlightcolor="#5A5A5A")
        self.layer_list.pack(fill="both", expand=True)
        self.layer_list.bind("<<ListboxSelect>>", self._on_layer_select)
        self.layer_list.bind("<Double-Button-1>", self._toggle_visible)

        row1 = ttk.Frame(frame)
        row1.pack(fill="x", pady=(8, 0))
        ttk.Button(row1, text="Add image", command=self._add_image).pack(side="left")
        ttk.Button(row1, text="Add text", command=self._add_text).pack(side="left", padx=4)

        row2 = ttk.Frame(frame)
        row2.pack(fill="x", pady=(4, 0))
        ttk.Button(row2, text="\u25b2 Up", width=7,
                   command=lambda: self._move_layer(1)).pack(side="left")
        ttk.Button(row2, text="\u25bc Down", width=8,
                   command=lambda: self._move_layer(-1)).pack(side="left", padx=4)
        ttk.Button(row2, text="Delete", command=self._delete_layer).pack(side="left")

    def _build_right(self, parent):
        right = ttk.Frame(parent)
        right.grid(row=0, column=2, sticky="nsew", padx=(14, 0))
        right.columnconfigure(0, weight=0)
        right.columnconfigure(1, weight=1)

        side = ttk.Frame(right)
        side.grid(row=0, column=0, sticky="n")

        self._build_colour(side)
        self._build_props(right)

        export = ttk.LabelFrame(side, text=" Export ", padding=10)
        export.grid(row=1, column=0, sticky="new", pady=(12, 0), padx=(0, 14))
        nrow = ttk.Frame(export)
        nrow.pack(anchor="w", fill="x")
        ttk.Label(nrow, text="File name:").pack(side="left")
        ttk.Entry(nrow, textvariable=self.var_filename,
                  width=22).pack(side="left", padx=6)
        brow = ttk.Frame(export)
        brow.pack(anchor="w", pady=(8, 0))
        ttk.Button(brow, text="Export .ico", style="Accent.TButton",
                   command=self._export_ico).pack(side="left")
        ttk.Button(brow, text="Export .png",
                   command=self._export_png).pack(side="left", padx=6)

    def _build_colour(self, parent):
        colour = ttk.LabelFrame(parent, text=" Colour ", padding=10)
        colour.grid(row=0, column=0, sticky="n", padx=(0, 14))

        row = ttk.Frame(colour)
        row.pack(anchor="w")
        self.swatches = {}
        for key, text in (("front", "Front"), ("back", "Back"), ("layer", "Layer")):
            cell = ttk.Frame(row)
            cell.pack(side="left", padx=(0, 8))
            sw = Swatch(cell, self.colors.get(key, (200, 200, 200)),
                        on_click=lambda k=key: self._select_target(k))
            sw.pack()
            ttk.Label(cell, text=text, style="Hint.TLabel").pack()
            self.swatches[key] = sw
        self.swatches["layer"].set_enabled(False)

        self.editing_label = ttk.Label(colour, text="", style="Hint.TLabel")
        self.editing_label.pack(anchor="w", pady=(6, 4))

        self.wheel = ColorWheel(colour, size=176, command=self._on_wheel)
        self.wheel.pack(anchor="w")

        hexrow = ttk.Frame(colour)
        hexrow.pack(anchor="w", pady=(8, 0))
        ttk.Label(hexrow, text="Hex:").pack(side="left")
        entry = ttk.Entry(hexrow, textvariable=self.var_hex, width=9)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", self._apply_hex)
        entry.bind("<FocusOut>", self._apply_hex)
        ttk.Button(hexrow, text="Pick...", width=7,
                   command=self._system_picker).pack(side="left")

    def _build_props(self, parent):
        props = ttk.LabelFrame(parent, text=" Properties ", padding=10)
        props.grid(row=0, column=1, sticky="new")

        self.prop_empty = ttk.Label(props, text="No layer selected.",
                                    style="Hint.TLabel")
        self.prop_body = ttk.Frame(props)

        ttk.Label(self.prop_body, text="Name").pack(anchor="w")
        self.name_label = ttk.Label(self.prop_body, text="-")
        self.name_label.pack(anchor="w")
        ttk.Checkbutton(self.prop_body, text="Visible", variable=self.var_visible,
                        command=self._on_prop_change).pack(anchor="w", pady=(4, 0))

        # image section
        self.sec_image = ttk.Frame(self.prop_body)
        ttk.Separator(self.sec_image, orient="horizontal").pack(fill="x", pady=6)
        ttk.Label(self.sec_image, text="Image", style="Hint.TLabel").pack(anchor="w")
        self.res_scale, self.lbl_res = self._add_slider(
            self.sec_image, "Resolution", self.var_res, 32, 1024,
            self._on_prop_change, "{:.0f} px")
        for value, text in (("original", "Original colours"),
                            ("solid", "Solid recolour"),
                            ("tint", "Tint")):
            ttk.Radiobutton(self.sec_image, text=text, value=value,
                            variable=self.var_recolor,
                            command=self._on_recolor).pack(anchor="w")
        bgrow = ttk.Frame(self.sec_image)
        bgrow.pack(anchor="w", pady=(6, 0))
        self.bg_btn = ttk.Button(bgrow, text="Remove background",
                                 command=self._remove_background)
        self.bg_btn.pack(side="left")
        self.undo_bg_btn = ttk.Button(bgrow, text="Undo", width=6,
                                      command=self._undo_background,
                                      state="disabled")
        self.undo_bg_btn.pack(side="left", padx=6)
        mrow = ttk.Frame(self.sec_image)
        mrow.pack(anchor="w", pady=(6, 0))
        ttk.Label(mrow, text="Model:").pack(side="left")
        ttk.Combobox(mrow, textvariable=self._bg_model, width=15,
                     state="readonly",
                     values=["u2net", "u2netp", "isnet-general-use",
                             "silueta"]).pack(side="left", padx=6)

        # text section
        self.sec_text = ttk.Frame(self.prop_body)
        ttk.Separator(self.sec_text, orient="horizontal").pack(fill="x", pady=6)
        ttk.Label(self.sec_text, text="Text", style="Hint.TLabel").pack(anchor="w")
        ttk.Entry(self.sec_text, textvariable=self.var_text,
                  width=26).pack(anchor="w", pady=(4, 0))
        self.var_text.trace_add("write", lambda *_: self._on_prop_change())
        frow = ttk.Frame(self.sec_text)
        frow.pack(anchor="w", fill="x", pady=(6, 0))
        self.font_combo = ttk.Combobox(frow, textvariable=self.var_font, width=20)
        self.font_combo.pack(side="left")
        self.font_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_prop_change())
        ttk.Button(frow, text="Add font...", width=11,
                   command=self._add_font).pack(side="left", padx=4)
        self.fontsize_scale, self.lbl_fontsize = self._add_slider(
            self.sec_text, "Size", self.var_fontsize, 8, 90,
            self._on_prop_change, "{:.0f} px")

        # transform section
        self.sec_transform = ttk.Frame(self.prop_body)
        ttk.Separator(self.sec_transform, orient="horizontal").pack(fill="x", pady=6)
        self.x_scale, self.lbl_x = self._add_slider(
            self.sec_transform, "X", self.var_x, -60, 60,
            self._on_prop_change, "{:.0f}")
        self.y_scale, self.lbl_y = self._add_slider(
            self.sec_transform, "Y", self.var_y, -60, 60,
            self._on_prop_change, "{:.0f}")
        self.scale_scale, self.lbl_scale = self._add_slider(
            self.sec_transform, "Scale", self.var_scale, 0.1, 4.0,
            self._on_prop_change)
        self.opacity_scale, self.lbl_opacity = self._add_slider(
            self.sec_transform, "Opacity", self.var_opacity, 0.0, 1.0,
            self._on_prop_change)

        # shadow section
        self.sec_shadow = ttk.Frame(self.prop_body)
        ttk.Separator(self.sec_shadow, orient="horizontal").pack(fill="x", pady=6)
        ttk.Checkbutton(self.sec_shadow, text="Drop shadow",
                        variable=self.var_shadow,
                        command=self._on_prop_change).pack(anchor="w")
        self.sdx_scale, self.lbl_sdx = self._add_slider(
            self.sec_shadow, "Shadow X", self.var_sdx, -30, 30,
            self._on_prop_change, "{:.0f}")
        self.sdy_scale, self.lbl_sdy = self._add_slider(
            self.sec_shadow, "Shadow Y", self.var_sdy, -30, 30,
            self._on_prop_change, "{:.0f}")
        self.sblur_scale, self.lbl_sblur = self._add_slider(
            self.sec_shadow, "Shadow blur", self.var_sblur, 0, 20,
            self._on_prop_change, "{:.1f}")
        self.sop_scale, self.lbl_sop = self._add_slider(
            self.sec_shadow, "Shadow opacity", self.var_sopacity, 0.0, 1.0,
            self._on_prop_change)

    def _add_slider(self, parent, label, var, lo, hi, cmd, fmt="{:.2f}"):
        row = ttk.Frame(parent)
        row.pack(anchor="w", fill="x", pady=(6, 0))
        ttk.Label(row, text=label).pack(side="left")
        value = ttk.Label(row, text=fmt.format(var.get()), style="Hint.TLabel")
        value.pack(side="right")
        scale = ttk.Scale(parent, from_=lo, to=hi, variable=var,
                          command=lambda v, f=fmt, l=value, c=cmd:
                          (l.config(text=f.format(float(v))), c()))
        scale.pack(anchor="w", fill="x")
        return scale, value

    # -- fonts ------------------------------------------------------------
    def _load_fonts(self):
        fonts = discover_fonts()
        self._results.put(lambda: self._set_fonts(fonts))

    def _set_fonts(self, fonts):
        self.fonts = fonts
        self._font_ready = True
        names = sorted(fonts.keys())
        self.font_combo["values"] = names
        if names:
            self.default_font = fonts[names[0]]
            for want in ("Arial", "Segoe UI", "Calibri", "Tahoma"):
                for label, path in fonts.items():
                    if label.startswith(want):
                        self.default_font = path
                        break
                else:
                    continue
                break
        if not self.var_font.get() and names:
            self.var_font.set(names[0])

    def _add_font(self):
        path = filedialog.askopenfilename(
            title="Choose a font",
            filetypes=[("Fonts", "*.ttf *.otf *.ttc"), ("All files", "*.*")])
        if not path:
            return
        label = font_label(path)
        self.fonts[label] = path
        self.font_combo["values"] = sorted(self.fonts.keys())
        self.var_font.set(label)
        self._on_prop_change()
        self.status.config(text=f"Added font: {label}")

    # -- layers -----------------------------------------------------------
    def _current_layer(self):
        if self.selected is None or not (0 <= self.selected < len(self.layers)):
            return None
        return self.layers[self.selected]

    def _layer_label(self, layer):
        mark = "\u25cf" if layer.visible else "\u25cb"
        tag = "IMG" if layer.kind == "image" else "TXT"
        return f" {mark}  {tag}  {layer.name}"

    def _refresh_layers(self):
        self.layer_list.delete(0, "end")
        for layer in reversed(self.layers):
            self.layer_list.insert("end", self._layer_label(layer))
        if self.selected is not None and 0 <= self.selected < len(self.layers):
            self.layer_list.selection_clear(0, "end")
            self.layer_list.selection_set(len(self.layers) - 1 - self.selected)
        self._refresh_props()

    def _refresh_selected_layer_row(self):
        if self.selected is None or not (0 <= self.selected < len(self.layers)):
            return
        row = len(self.layers) - 1 - self.selected
        self.layer_list.delete(row)
        self.layer_list.insert(row, self._layer_label(self.layers[self.selected]))
        self.layer_list.selection_clear(0, "end")
        self.layer_list.selection_set(row)

    def _on_layer_select(self, _event=None):
        sel = self.layer_list.curselection()
        if not sel:
            return
        self.selected = len(self.layers) - 1 - sel[0]
        self._refresh_props()
        self._sync_layer_swatch()

    def _add_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            image = load_image(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_NAME, f"Could not open image:\n{exc}")
            return
        layer = ImageLayer(image, f"Image {sum(1 for l in self.layers if l.kind == 'image') + 1}")
        self.layers.append(layer)
        self.selected = len(self.layers) - 1
        self._refresh_layers()
        self._sync_layer_swatch()
        self.status.config(text=f"Added {elide(os.path.basename(path))}")
        self._schedule_preview()

    def _add_text(self):
        if self.default_font is None:
            messagebox.showinfo(APP_NAME, "Fonts are still loading, try again.")
            return
        layer = TextLayer("Text", self.default_font,
                          f"Text {sum(1 for l in self.layers if l.kind == 'text') + 1}")
        self.layers.append(layer)
        self.selected = len(self.layers) - 1
        self._refresh_layers()
        self._sync_layer_swatch()
        self._schedule_preview()

    def _delete_layer(self):
        if self.selected is None:
            return
        del self.layers[self.selected]
        self.selected = min(self.selected, len(self.layers) - 1) if self.layers else None
        self._refresh_layers()
        self._sync_layer_swatch()
        self._schedule_preview()

    def _move_layer(self, direction):
        i = self.selected
        if i is None:
            return
        j = i + direction
        if not (0 <= j < len(self.layers)):
            return
        self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
        self.selected = j
        self._refresh_layers()
        self._schedule_preview()

    def _toggle_visible(self, _event=None):
        layer = self._current_layer()
        if layer is None:
            return
        layer.visible = not layer.visible
        self.var_visible.set(layer.visible)
        self._refresh_layers()
        self._schedule_preview()

    # -- property syncing -------------------------------------------------
    def _refresh_props(self):
        layer = self._current_layer()
        for section in (self.sec_image, self.sec_text,
                        self.sec_transform, self.sec_shadow):
            section.pack_forget()
        if layer is None:
            self.prop_body.pack_forget()
            self.prop_empty.pack(anchor="w")
            self.swatches["layer"].set_enabled(False)
            return
        self.prop_empty.pack_forget()
        self.prop_body.pack(anchor="w", fill="x")

        self._loading = True
        try:
            self.name_label.config(text=layer.name)
            self.var_visible.set(layer.visible)
            self.var_x.set(layer.x)
            self.var_y.set(layer.y)
            self.var_scale.set(layer.scale)
            self.var_opacity.set(layer.opacity)
            self.var_shadow.set(layer.shadow.enabled)
            self.var_sdx.set(layer.shadow.dx)
            self.var_sdy.set(layer.shadow.dy)
            self.var_sblur.set(layer.shadow.blur)
            self.var_sopacity.set(layer.shadow.opacity)

            if layer.kind == "image":
                self.var_res.set(layer.source_res)
                self.var_recolor.set(layer.recolor_mode)
            else:
                self.var_text.set(layer.text)
                self.var_fontsize.set(layer.font_size)
        finally:
            self._loading = False

        self.lbl_x.config(text=f"{layer.x:.0f}")
        self.lbl_y.config(text=f"{layer.y:.0f}")
        self.lbl_scale.config(text=f"{layer.scale:.2f}")
        self.lbl_opacity.config(text=f"{layer.opacity:.2f}")
        self.lbl_sdx.config(text=f"{layer.shadow.dx:.0f}")
        self.lbl_sdy.config(text=f"{layer.shadow.dy:.0f}")
        self.lbl_sblur.config(text=f"{layer.shadow.blur:.1f}")
        self.lbl_sop.config(text=f"{layer.shadow.opacity:.2f}")

        if layer.kind == "image":
            self.lbl_res.config(text=f"{layer.source_res:.0f} px")
            self.sec_image.pack(anchor="w", fill="x")
        else:
            self.lbl_fontsize.config(text=f"{layer.font_size:.0f} px")
            self.sec_text.pack(anchor="w", fill="x")
        self.sec_transform.pack(anchor="w", fill="x")
        self.sec_shadow.pack(anchor="w", fill="x")
        self.swatches["layer"].set_enabled(True)
        self._sync_layer_swatch()

    def _sync_layer_swatch(self):
        layer = self._current_layer()
        if layer is None:
            self.swatches["layer"].set_enabled(False)
            return
        self.swatches["layer"].set_enabled(True)
        self.swatches["layer"].set_color(layer.color)
        if self.active == "layer":
            self.wheel.set_rgb(layer.color, fire=False)
            self.var_hex.set(rgb_to_hex(layer.color))

    def _on_prop_change(self):
        if self._loading:
            return
        layer = self._current_layer()
        if layer is None:
            return
        old_visible = layer.visible
        layer.visible = bool(self.var_visible.get())
        layer.x = float(self.var_x.get())
        layer.y = float(self.var_y.get())
        layer.scale = float(self.var_scale.get())
        layer.opacity = float(self.var_opacity.get())
        layer.shadow.enabled = bool(self.var_shadow.get())
        layer.shadow.dx = float(self.var_sdx.get())
        layer.shadow.dy = float(self.var_sdy.get())
        layer.shadow.blur = float(self.var_sblur.get())
        layer.shadow.opacity = float(self.var_sopacity.get())
        if layer.kind == "image":
            layer.source_res = int(round(self.var_res.get()))
        else:
            layer.text = self.var_text.get()
            layer.font_size = float(self.var_fontsize.get())
            label = self.var_font.get()
            if label in self.fonts:
                layer.font_path = self.fonts[label]
        if layer.visible != old_visible:
            self._refresh_selected_layer_row()
        self._schedule_preview()

    def _on_recolor(self):
        layer = self._current_layer()
        if layer is None or layer.kind != "image":
            return
        layer.recolor_mode = self.var_recolor.get()
        if layer.recolor_mode != "original":
            self._select_target("layer")
        self._refresh_layers()
        self._schedule_preview()

    # -- colour targets ---------------------------------------------------
    def _select_target(self, key):
        if key == "layer" and self._current_layer() is None:
            return
        self.active = key
        for k, sw in self.swatches.items():
            sw.set_active(k == key)
        names = {"front": "Front", "back": "Back", "layer": "Layer"}
        self.editing_label.config(text=f"Editing: {names[key]}")
        if key == "layer":
            layer = self._current_layer()
            self.wheel.set_rgb(layer.color, fire=False)
            self.var_hex.set(rgb_to_hex(layer.color))
        else:
            self.wheel.set_rgb(self.colors[key], fire=False)
            self.var_hex.set(rgb_to_hex(self.colors[key]))

    def _on_wheel(self, rgb):
        if self.active == "layer":
            layer = self._current_layer()
            if layer is None:
                return
            layer.color = rgb
            self.swatches["layer"].set_color(rgb)
        else:
            self.colors[self.active] = rgb
            self.swatches[self.active].set_color(rgb)
        self.var_hex.set(rgb_to_hex(rgb))
        self._schedule_preview()

    def _apply_hex(self, _event=None):
        try:
            rgb = hex_to_rgb(self.var_hex.get())
        except ValueError:
            return
        self._on_wheel(rgb)
        self.wheel.set_rgb(rgb, fire=False)

    def _system_picker(self):
        if self.active == "layer" and self._current_layer() is not None:
            initial = rgb_to_hex(self._current_layer().color)
        else:
            initial = rgb_to_hex(self.colors.get(self.active, (200, 200, 200)))
        result = colorchooser.askcolor(color=initial, title="Choose colour")
        if result and result[0]:
            rgb = tuple(int(round(c)) for c in result[0])
            self._on_wheel(rgb)
            self.wheel.set_rgb(rgb, fire=False)

    # -- background removal ----------------------------------------------
    def _remove_background(self):
        layer = self._current_layer()
        if layer is None or layer.kind != "image":
            messagebox.showinfo(APP_NAME, "Select an image layer first.")
            return
        model = self._bg_model.get()
        self.bg_btn.config(state="disabled")
        self.status.config(text=f"Removing background with '{model}' "
                                f"(first run downloads the model)...")
        src = layer.image_original.copy()
        threading.Thread(target=self._bg_worker, args=(layer, src, model),
                         daemon=True).start()

    def _bg_worker(self, layer, src, model):
        try:
            from rembg import new_session, remove
        except ImportError:
            self._results.put(self._offer_install)
            return
        try:
            session = self._sessions.get(model)
            if session is None:
                session = new_session(model)
                self._sessions[model] = session
            cut = autocrop(remove(src, session=session))
        except Exception as exc:  # noqa: BLE001
            self._results.put(lambda e=exc: self._bg_failed(e))
            return
        self._results.put(lambda: self._bg_done(layer, cut))

    def _bg_done(self, layer, cut):
        self.bg_btn.config(state="normal")
        if layer in self.layers:
            layer.image = cut
            self.undo_bg_btn.config(state="normal")
            self.status.config(text="Background removed.")
            self._schedule_preview()
        else:
            self.status.config(text="Background removal finished; layer was deleted.")

    def _bg_failed(self, exc):
        self.bg_btn.config(state="normal")
        self.status.config(text="Background removal failed.")
        messagebox.showerror(APP_NAME, f"Background removal failed:\n{exc}")

    def _undo_background(self):
        layer = self._current_layer()
        if layer is None or layer.kind != "image":
            return
        layer.image = layer.image_original
        self.undo_bg_btn.config(state="disabled")
        self.status.config(text="Restored the original image.")
        self._schedule_preview()

    def _offer_install(self):
        self.bg_btn.config(state="normal")
        if messagebox.askyesno(
                APP_NAME,
                "The 'rembg' package is not installed.\n\n"
                "Install it now with pip? This needs an internet "
                "connection and takes a minute or two."):
            self.status.config(text="Installing rembg...")
            threading.Thread(target=self._pip_install, daemon=True).start()

    def _pip_install(self):
        import subprocess
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "rembg"],
                           check=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as exc:  # noqa: BLE001
            self._results.put(lambda e=exc: messagebox.showerror(
                APP_NAME, f"Could not install rembg:\n{e}"))
            return
        self._results.put(lambda: self.status.config(
            text="rembg installed - click 'Remove background' again."))

    # -- preview view -----------------------------------------------------
    def _on_zoom(self, value):
        self.view_zoom = clamp(float(value), ZOOM_MIN, ZOOM_MAX)
        self._fast = True
        self._request_full_after()
        self._schedule_preview()

    def _fit_view(self):
        self.view_zoom = 2.6
        self.var_zoom.set(self.view_zoom)
        self.pan_x = self.pan_y = 0.0
        self._schedule_preview()

    def _wheel(self, event):
        delta = getattr(event, "delta", 0)
        if delta == 0:
            delta = 120 if getattr(event, "num", 0) == 4 else -120
        old = self.view_zoom
        new = clamp(old * (1.12 if delta > 0 else 1 / 1.12), ZOOM_MIN, ZOOM_MAX)
        if abs(new - old) < 1e-6:
            return
        cw = self.preview.winfo_width()
        ch = self.preview.winfo_height()
        cx = event.x - cw / 2.0
        cy = event.y - ch / 2.0
        ix = (cx - self.pan_x) / old
        iy = (cy - self.pan_y) / old
        self.view_zoom = new
        self.var_zoom.set(new)
        self.pan_x = cx - ix * new
        self.pan_y = cy - iy * new
        self._fast = True
        self._request_full_after()
        self._schedule_preview()

    def _canvas_to_design(self, cx, cy):
        ox, oy = self._icon_origin
        return (cx - ox) / self.view_zoom, (cy - oy) / self.view_zoom

    def _set_preview_cursor(self):
        tool = self.var_tool.get()
        if tool == "erase":
            cursor = "none"
        elif tool == "restore":
            cursor = "crosshair"
        else:
            cursor = "fleur"
        try:
            self.preview.config(cursor=cursor)
        except tk.TclError:
            self.preview.config(cursor="crosshair" if tool == "erase" else cursor)

    def _redraw_tool_cursor(self):
        if not hasattr(self, "preview"):
            return
        self.preview.delete("tool_cursor")
        if self.var_tool.get() != "erase" or self._cursor_pos is None:
            return
        x, y = self._cursor_pos
        self.preview.create_image(x + 9, y + 9, anchor="center",
                                  image=self._eraser_cursor,
                                  tags="tool_cursor")

    def _preview_hover(self, event):
        self._cursor_pos = (event.x, event.y)
        self._redraw_tool_cursor()

    def _preview_leave(self, _event):
        self._cursor_pos = None
        self.preview.delete("tool_cursor")

    def _hit_layer(self, dx, dy):
        for i in range(len(self.layers) - 1, -1, -1):
            layer = self.layers[i]
            if not layer.visible:
                continue
            x0, y0, x1, y1 = layer.bbox_design()
            if x0 <= dx <= x1 and y0 <= dy <= y1:
                return i
        return None

    def _preview_press(self, event):
        dx, dy = self._canvas_to_design(event.x, event.y)
        i = self._hit_layer(dx, dy)
        if self.var_tool.get() in ("erase", "restore"):
            if i is None:
                self._drag = ("pan", event.x, event.y, self.pan_x, self.pan_y)
                return
            if i != self.selected:
                self.selected = i
                self._refresh_layers()
            self._last_paint = None
            self._paint(dx, dy)
            self._drag = ("paint",)
            return
        if i is not None:
            layer = self.layers[i]
            self.selected = i
            self._refresh_layers()
            self._drag = ("layer", i, dx, dy, layer.x, layer.y)
            return
        self._drag = ("pan", event.x, event.y, self.pan_x, self.pan_y)

    def _preview_motion(self, event):
        if self._drag is None:
            return
        self._cursor_pos = (event.x, event.y)
        self._redraw_tool_cursor()
        self._fast = True
        self._request_full_after()
        if self._drag[0] == "paint":
            dx, dy = self._canvas_to_design(event.x, event.y)
            self._paint(dx, dy)
            return
        if self._drag[0] == "layer":
            _, i, dx0, dy0, x0, y0 = self._drag
            dx, dy = self._canvas_to_design(event.x, event.y)
            layer = self.layers[i]
            layer.x = clamp(x0 + (dx - dx0), -80, 80)
            layer.y = clamp(y0 + (dy - dy0), -80, 80)
            self._loading = True
            try:
                self.var_x.set(layer.x)
                self.var_y.set(layer.y)
            finally:
                self._loading = False
            self.lbl_x.config(text=f"{layer.x:.0f}")
            self.lbl_y.config(text=f"{layer.y:.0f}")
            self._schedule_preview()
        else:
            _, x0, y0, px, py = self._drag
            self.pan_x = px + (event.x - x0)
            self.pan_y = py + (event.y - y0)
            self._schedule_preview(icon_dirty=False)

    def _preview_release(self, _event):
        self._drag = None
        self._last_paint = None
        if self._fast:
            self._fast = False
            self._schedule_preview()

    def _paint(self, dx, dy):
        layer = self._current_layer()
        if layer is None:
            return
        restore = self.var_tool.get() == "restore"
        radius = float(self.var_brush.get())
        opacity = float(self.var_eraser_opacity.get())
        if self._last_paint is not None:
            lx, ly = self._last_paint
            steps = max(1, int(math.hypot(dx - lx, dy - ly)
                               / max(0.5, radius * 0.5)))
            for s in range(1, steps + 1):
                t = s / steps
                layer.erase_at(lx + (dx - lx) * t, ly + (dy - ly) * t,
                               radius, restore, opacity)
        else:
            layer.erase_at(dx, dy, radius, restore, opacity)
        self._last_paint = (dx, dy)
        self._schedule_preview()

    def _clear_eraser(self):
        layer = self._current_layer()
        if layer is None:
            return
        layer.clear_mask()
        self.status.config(text="Eraser cleared.")
        self._schedule_preview()

    def _on_tool(self):
        self._set_preview_cursor()
        self._redraw_tool_cursor()
        if self.var_tool.get() == "move":
            text = ("Left-drag a layer to move it \u00b7 right-drag to pan "
                    "\u00b7 wheel to zoom")
        else:
            word = "Erase" if self.var_tool.get() == "erase" else "Restore"
            text = (f"{word}: drag on the icon to paint on the selected layer "
                    f"\u00b7 right-drag to pan \u00b7 wheel to zoom")
        if hasattr(self, "tool_hint"):
            self.tool_hint.config(text=text)

    def _pan_press(self, event):
        self._drag = ("pan", event.x, event.y, self.pan_x, self.pan_y)

    def _pan_motion(self, event):
        if self._drag and self._drag[0] == "pan":
            self._preview_motion(event)

    # -- rendering --------------------------------------------------------
    def _schedule_preview(self, *_, icon_dirty=True):
        if icon_dirty:
            self._preview_icon_dirty = True
        if self._render_job is None:
            self._render_job = self.after(15, self._update_preview)

    def _render(self, size, ss):
        return render_document(size, ss, self.colors["front"],
                               self.colors["back"], self.layers)

    def _update_preview(self):
        self._render_job = None
        cw = self.preview.winfo_width() or 420
        ch = self.preview.winfo_height() or 420
        disp = max(16, int(round(DESIGN * self.view_zoom)))
        ss = 1 if (self._fast or disp > 420) else 2
        icon_key = (disp, ss)
        if (self._preview_icon_dirty or self._preview_icon is None or
                self._preview_icon_key != icon_key):
            self._preview_icon = self._render(disp, ss)
            self._preview_icon_key = icon_key
            self._preview_icon_dirty = False
        icon = self._preview_icon
        checker = self._checker_cache.get((cw, ch))
        if checker is None:
            checker = make_checker(max(cw, ch)).crop((0, 0, cw, ch))
            self._checker_cache[(cw, ch)] = checker
        canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        canvas.alpha_composite(checker, (0, 0))
        ox = int(round(cw / 2 - disp / 2 + self.pan_x))
        oy = int(round(ch / 2 - disp / 2 + self.pan_y))
        self._icon_origin = (ox, oy)
        canvas.alpha_composite(icon, (ox, oy))
        self._preview_photo = ImageTk.PhotoImage(canvas)
        self.preview.delete("all")
        self.preview.create_image(0, 0, anchor="nw", image=self._preview_photo)
        self._redraw_tool_cursor()

    def _request_full_after(self, delay=180):
        if self._full_job is not None:
            self.after_cancel(self._full_job)
        self._full_job = self.after(delay, self._finish_fast)

    def _finish_fast(self):
        self._full_job = None
        self._fast = False
        self._schedule_preview()

    # -- export -----------------------------------------------------------
    def _export(self, ext, label):
        name = self.var_filename.get().strip() or "folder"
        path = filedialog.asksaveasfilename(
            title=f"Save {label}", defaultextension=ext,
            initialfile=name + ext,
            filetypes=[(label, f"*{ext}"), ("All files", "*.*")])
        if not path:
            return
        self.status.config(text="Rendering...")
        self.update_idletasks()
        try:
            master = self._render(1024, ss=2)
            if ext == ".ico":
                master.save(path, format="ICO", sizes=ICO_SIZES)
            else:
                master.save(path, format="PNG")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_NAME, f"Export failed:\n{exc}")
            self.status.config(text="Export failed.")
            return
        self.status.config(text=f"Saved {path}")

    def _export_ico(self):
        self._export(".ico", "Icon")

    def _export_png(self):
        self._export(".png", "PNG image")


def _set_app_user_model_id():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except OSError:
        pass


def main():
    _set_app_user_model_id()
    App().mainloop()


if __name__ == "__main__":
    main()
