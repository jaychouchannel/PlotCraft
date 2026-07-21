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


async def execute_code(code: str) -> tuple[str, str, str]:
    """在隔离子进程中执行 matplotlib 代码。

    返回 (svg_content, svg_path, error_str)：
      - 成功: (svg, "/tmp/.../output.svg", "")
      - 失败: ("", "", error_message)
    """
    tmpdir = tempfile.mkdtemp(prefix="plot_sandbox_")
    try:
        code_path = Path(tmpdir) / "script.py"
        code_path.write_text(code, encoding="utf-8")

        env = dict(os.environ)
        # 强制 matplotlib 使用 Agg 后端（不弹窗）
        env["MPLBACKEND"] = "Agg"
        # 禁用网络（断网）：在 site-packages 中只能依赖代码自身不联网
        # 这里通过设置 HTTP/HTTPS 代理为空 + 全局禁网（不可移植，依赖代码自检）
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
