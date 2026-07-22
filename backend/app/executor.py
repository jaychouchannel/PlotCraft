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

# 注入到用户代码末尾的多格式保存 hook：
# - 优先用 matplotlib 当前 figure（plt.gcf()），若已 close 则重新读 SVG 也无能为力
# - 安全 try/except，任一格式失败不影响 svg 主流程
_MULTIFORMAT_HOOK = '''

# --- PlotCraft: 多格式导出 hook（不影响 svg 主输出） ---
try:
    import matplotlib.pyplot as _pc_plt
    _pc_fig = _pc_plt.gcf()
    if _pc_fig.get_size_inches().sum() > 0:
        _pc_fig.savefig("output.png", dpi=300, bbox_inches="tight")
        _pc_fig.savefig("output.pdf", bbox_inches="tight")
except Exception as _pc_e:
    pass
# --- hook end ---
'''


async def execute_code(code: str) -> tuple[str, str, str]:
    """在隔离子进程中执行 matplotlib 代码。

    返回 (svg_content, svg_path, error_str)：
      - 成功: (svg, "/tmp/.../output.svg", "")
      - 失败: ("", "", error_message)
    """
    async with _sem:
        tmpdir = tempfile.mkdtemp(prefix="plot_sandbox_")
        try:
            code_path = Path(tmpdir) / "script.py"
            code_path.write_text(code + "\n" + _MULTIFORMAT_HOOK, encoding="utf-8")

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
    fmt = fmt.lower()
    if fmt not in ("png", "pdf", "svg"):
        return b"", f"不支持的格式: {fmt}"

    async with _sem:
        tmpdir = tempfile.mkdtemp(prefix="plot_sandbox_")
        try:
            code_path = Path(tmpdir) / "script.py"
            hook = _MULTIFORMAT_HOOK.replace('"output.png"', f'"output.{fmt}"') if fmt != "png" else _MULTIFORMAT_HOOK
            if fmt == "pdf":
                hook = '''
try:
    import matplotlib.pyplot as _pc_plt
    _pc_fig = _pc_plt.gcf()
    if _pc_fig.get_size_inches().sum() > 0:
        _pc_fig.savefig("output.pdf", bbox_inches="tight")
except Exception:
    pass
'''
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
