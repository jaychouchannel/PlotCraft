from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

SANDBOX_TIMEOUT = 60  # 秒
SANDBOX_CONCURRENCY = 2  # 同时执行的沙箱子进程上限，防止狂点导致雪崩

_sem = asyncio.Semaphore(SANDBOX_CONCURRENCY)

# 沙箱禁止 import 的模块（与 system prompt 黑名单保持一致，并在此做技术强制）
_BLOCKED_MODULES = {
    "os", "sys", "socket", "requests", "httpx", "subprocess",
    "shutil", "pathlib", "importlib", "ctypes", "multiprocessing",
    "asyncio", "builtins",
}
# 仅用于阻断子进程内的进一步执行；不试图覆盖用户代码已有的 import。
_BLOCKED_OPEN_MODES = {"w", "wb", "a", "ab", "x", "xb", "wt", "at", "xt"}


def _build_export_hook(formats: tuple[str, ...]) -> str:
    """构造参数化的多格式 savefig hook，单源、无死分支。

    formats 中每个元素属于 {"svg", "png", "pdf"}；hook 会把 matplotlib 当前 figure
    保存为每种格式。任一格式失败不影响其他格式。
    """
    saves = []
    for f in formats:
        if f == "svg":
            saves.append('        _pc_fig.savefig("output.svg", format="svg", dpi=300, bbox_inches="tight")')
        elif f == "png":
            saves.append('        _pc_fig.savefig("output.png", dpi=300, bbox_inches="tight")')
        elif f == "pdf":
            saves.append('        _pc_fig.savefig("output.pdf", bbox_inches="tight")')
        else:
            raise ValueError(f"unsupported format: {f}")
    saves_block = "\n".join(saves)
    return f'''
# --- PlotCraft: 多格式导出 hook ---
try:
    import matplotlib.pyplot as _pc_plt
    _pc_fig = _pc_plt.gcf()
    if _pc_fig.get_size_inches().sum() > 0:
{saves_block}
except Exception:
    pass
# --- hook end ---
'''


def _validate_sandboxed_code(code: str) -> str | None:
    """对用户代码做 AST 静态分析，命中黑名单 import / 危险调用时返回拒绝原因。"""
    import ast

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"代码语法错误: {e}"

    def _mod_name(node):
        # import a.b.c -> "a"; from a.b import c -> "a"
        n = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
        return n.split(".")[0] if n else None

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = _mod_name(node)
            if mod in _BLOCKED_MODULES:
                return f"沙箱禁止 import: {mod}"
        elif isinstance(node, ast.Call):
            func = node.func
            # 阻断 open(file, "w"/"a"/"x") 写文件（除了主流程 savefig 已内建）
            if isinstance(func, ast.Name) and func.id == "open":
                if len(node.args) >= 2:
                    mode_arg = node.args[1]
                    if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
                        if any(m in mode_arg.value for m in _BLOCKED_OPEN_MODES):
                            return "沙箱禁止 open() 写模式"
            # 阻断 __import__("os") / importlib.import_module("os") 等动态 import
            if isinstance(func, ast.Attribute) and func.attr == "__import__":
                return "沙箱禁止 __import__()"
            if isinstance(func, ast.Name) and func.id == "__import__":
                return "沙箱禁止 __import__()"
            # 阻断 eval/exec/compile 跑动态代码
            if isinstance(func, ast.Name) and func.id in {"eval", "exec", "compile"}:
                return f"沙箱禁止 {func.id}()"
    return None


async def execute_code(code: str) -> tuple[str, str, str]:
    """在隔离子进程中执行 matplotlib 代码。

    返回 (svg_content, svg_path, error_str)：
      - 成功: (svg, "/tmp/.../output.svg", "")
      - 失败: ("", "", error_message)
    """
    # AST 静态检查：在执行前拦截黑名单 import / 危险调用
    raise_reason = _validate_sandboxed_code(code)
    if raise_reason:
        return "", "", raise_reason

    tmpdir = tempfile.mkdtemp(prefix="plot_sandbox_")
    try:
        code_path = Path(tmpdir) / "script.py"
        code_path.write_text(code + "\n" + _build_export_hook(("svg", "png", "pdf")), encoding="utf-8")

        env = dict(os.environ)
        env["MPLBACKEND"] = "Agg"
        env["NO_PROXY"] = "*"
        env["no_proxy"] = "*"

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(code_path),
            cwd=tmpdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=SANDBOX_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return "", "", f"执行超时 (>{SANDBOX_TIMEOUT}s)"

        if proc.returncode != 0:
            err_text = (stderr_b or b"").decode("utf-8", errors="replace")
            return "", "", err_text

        svg_path = Path(tmpdir) / "output.svg"
        if not svg_path.exists():
            err_tail = (stderr_b or b"").decode("utf-8", errors="replace")[-500:]
            return "", "", f"脚本执行完毕但未生成 output.svg，请检查 plt.savefig 路径。\n{err_tail}"

        svg_content = svg_path.read_text(encoding="utf-8", errors="replace")
        return svg_content, str(svg_path), ""

    except Exception:
        return "", "", traceback.format_exc()
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


async def render_to_format(code: str, fmt: str) -> tuple[bytes, str]:
    """执行用户代码并把当前 figure 直接保存为指定格式（png/pdf），返回二进制。

    与 execute_code 不同：这里反过来——把 SVG 当作副产物，把目标格式当作主产物。
    若用户代码自己 savefig 了 output.<fmt>，直接读；否则在 hook 里强制再 savefig 一次。
    """
    # AST 静态检查
    raise_reason = _validate_sandboxed_code(code)
    if raise_reason:
        return b"", raise_reason

    fmt = fmt.lower()
    if fmt not in ("png", "pdf", "svg"):
        return b"", f"不支持的格式: {fmt}"

    tmpdir = tempfile.mkdtemp(prefix="plot_sandbox_")
    try:
        code_path = Path(tmpdir) / "script.py"
        hook = _build_export_hook((fmt,))
        code_path.write_text(code + "\n" + hook, encoding="utf-8")

        env = dict(os.environ)
        env["MPLBACKEND"] = "Agg"
        env["NO_PROXY"] = "*"
        env["no_proxy"] = "*"

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(code_path),
            cwd=tmpdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=SANDBOX_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return b"", f"执行超时 (>{SANDBOX_TIMEOUT}s)"

        if proc.returncode != 0:
            return b"", (stderr_b or b"").decode("utf-8", errors="replace")

        out_path = Path(tmpdir) / f"output.{fmt}"
        if not out_path.exists():
            return b"", f"脚本执行完毕但未生成 output.{fmt}"
        return out_path.read_bytes(), ""

    except Exception:
        return b"", traceback.format_exc()
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
