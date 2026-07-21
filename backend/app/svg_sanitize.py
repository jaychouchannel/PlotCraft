"""SVG 消毒：移除脚本、事件处理器、外部引用，防 XSS。

_strategy: 用 xml.etree 解析 SVG，遍历所有元素和属性，按白名单保留。
"""
from __future__ import annotations

import re
from xml.etree import ElementTree as ET

# 允许的 SVG 元素白名单
_ALLOWED_TAGS = {
    "svg", "g", "defs", "style", "rect", "circle", "ellipse", "line",
    "polyline", "polygon", "path", "text", "tspan", "title", "desc",
    "use", "symbol", "linearGradient", "radialGradient", "stop",
    "clipPath", "mask", "pattern", "image", "marker", "markerStart",
    "markerMid", "markerEnd", "textPath", "tref", "switch", "image",
}

# 允许的属性白名单前缀（属性名小写后做前缀匹配）
_ALLOWED_ATTR_PREFIXES = (
    "id", "class", "style", "transform", "cx", "cy", "r", "rx", "ry",
    "x", "y", "x1", "y1", "x2", "y2", "width", "height", "d", "points",
    "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
    "stroke-dasharray", "stroke-dashoffset", "fill-opacity", "stroke-opacity",
    "opacity", "font", "text", "text-anchor", "text-decoration",
    "font-family", "font-size", "font-weight", "font-style", "letter-spacing",
    "word-spacing", "writing-mode", "visibility", "display", "color",
    "gradient", "gradienttransform", "gradientunits", "spreadmethod",
    "offset", "stop-color", "stop-opacity", "clip", "clip-path", "clip-rule",
    "mask", "marker", "pattern", "patternunits", "patterntransform",
    "viewbox", "preserveaspectratio", "xmlns", "version",
    "xlink:href", "href",  # 这里仍可能引入外部资源，下面会过滤
)

# 完全禁止的属性（事件处理器、脚本入口）
_FORBIDDEN_ATTR_PATTERNS = (
    re.compile(r"^on", re.IGNORECASE),  # onclick onmouseover 等
)

# xlink/href 不允许 javascript:、data:、外部 URL（只允许同文档内引用 #id）
_HREF_BAD = re.compile(r"^\s*(javascript|data|https?|file|ftp):", re.IGNORECASE)


def sanitize_svg(svg: str) -> str:
    """返回消毒后的 SVG 字符串；解析失败时返回空串避免泄露原始内容。"""
    if not svg:
        return ""
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=False))
        root = ET.fromstring(svg, parser=parser)
    except Exception:
        return ""

    _walk_strip(root)
    return ET.tostring(root, encoding="unicode")


def _walk_strip(elem: ET.Element) -> None:
    # 1. 删除不在白名单的子元素
    for child in list(elem):
        if _strip_tag(child.tag) not in _ALLOWED_TAGS:
            elem.remove(child)
        else:
            _walk_strip(child)

    # 2. 清洗属性
    for name in list(elem.attrib.keys()):
        lc = name.lower()
        if any(p.match(lc) for p in _FORBIDDEN_ATTR_PATTERNS):
            del elem.attrib[name]
            continue
        # 检查白名单前缀
        if not any(lc == p or lc.startswith(p) for p in _ALLOWED_ATTR_PREFIXES):
            del elem.attrib[name]
            continue
        # href / xlink:href 内容检查
        if lc.endswith(":href") or lc == "href":
            val = elem.attrib[name].strip()
            if val.startswith("#"):
                continue  # 同文档引用，安全
            if _HREF_BAD.match(val):
                del elem.attrib[name]
                continue


def _strip_tag(tag: str) -> str:
    # ET 用 {namespace}local 形式表示带命名空间的 tag，去掉命名空间后比较
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag
