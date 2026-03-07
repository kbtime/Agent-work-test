#!/usr/bin/env python3
"""
课程大纲解析脚本（方案A：Python提取结构 + Haiku分析）
步骤1：python-docx 将 DOCX 转为结构化 Markdown（保留标题层级、列表、表格）
步骤2：claude-haiku-4-5 从结构化 Markdown 中提取字段，生成解析结果

用法：
    python course_parser.py [--input <输入目录>] [--output <输出目录>] [--prompt <Prompt文件>]

默认路径（相对于脚本所在位置向上两级的 program 目录）：
    输入：02_课程大纲库/01_原始课纲/
    输出：02_课程大纲库/02_课纲解析结果/
    Prompt：<project>/Training/dmeo/课程解析Prompt.md
"""

import argparse
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("❌ 缺少依赖：anthropic")
    print("请安装：pip install anthropic")
    sys.exit(1)

SUPPORTED_EXTENSIONS = {".docx", ".md"}


# ── 步骤1：DOCX / MD → 结构化 Markdown ───────────────────────────────────────

def _runs_to_md(paragraph) -> str:
    """将段落中的 runs 转为 Markdown 行内格式（保留粗体/斜体）。"""
    parts = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        if run.bold and run.italic:
            text = f"***{text}***"
        elif run.bold:
            text = f"**{text}**"
        elif run.italic:
            text = f"*{text}*"
        parts.append(text)
    return "".join(parts).strip()


def _is_list_paragraph(paragraph) -> bool:
    """判断段落是否为列表项（通过样式名或 numPr XML 元素）。"""
    style = paragraph.style.name
    if style in {"List Paragraph", "List Bullet", "List Number",
                 "List Bullet 2", "List Bullet 3", "List Number 2"}:
        return True
    pPr = paragraph._p.pPr
    return pPr is not None and pPr.numPr is not None


def _list_indent_level(paragraph) -> int:
    """返回列表缩进层级（0-based），用于生成嵌套列表。"""
    try:
        pPr = paragraph._p.pPr
        if pPr is not None and pPr.numPr is not None:
            ilvl = pPr.numPr.ilvl
            if ilvl is not None:
                return int(ilvl.val)
    except Exception:
        pass
    return 0


def _para_to_md(paragraph) -> str | None:
    """将单个段落转为 Markdown 字符串，无内容返回 None。"""
    style = paragraph.style.name

    if style.startswith("Heading"):
        parts = style.split()
        try:
            level = int(parts[-1])
        except (ValueError, IndexError):
            level = 1
        text = paragraph.text.strip()
        if not text:
            return None
        return "#" * min(level, 6) + " " + text

    text = _runs_to_md(paragraph)
    if not text:
        return None

    if _is_list_paragraph(paragraph):
        indent = "  " * _list_indent_level(paragraph)
        return f"{indent}- {text}"

    return text


def _table_to_md(table) -> str:
    """将 docx 表格转为 Markdown 表格。"""
    rows = []
    for i, row in enumerate(table.rows):
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows)


def read_docx(path: Path) -> str:
    """将 DOCX 转为结构化 Markdown（标题层级 / 列表 / 表格 / 粗斜体）。"""
    try:
        from docx import Document
        from docx.text.paragraph import Paragraph
        from docx.table import Table
    except ImportError:
        raise ImportError("缺少依赖：python-docx，请安装：pip install python-docx")

    doc = Document(path)
    parts = []
    for block in doc.element.body:
        tag = block.tag.split("}")[-1]
        if tag == "p":
            md = _para_to_md(Paragraph(block, doc))
            if md:
                parts.append(md)
        elif tag == "tbl":
            md = _table_to_md(Table(block, doc))
            if md:
                parts.append(md)
    return "\n\n".join(parts)


def read_md(path: Path) -> str:
    """读取 Markdown 文件（直接返回原始内容）。"""
    return path.read_text(encoding="utf-8")


def read_course_file(path: Path) -> str:
    """根据文件扩展名分发到对应的读取函数。"""
    ext = path.suffix.lower()
    dispatch = {".docx": read_docx, ".md": read_md}
    if ext not in dispatch:
        raise ValueError(f"不支持的文件类型：{ext}")
    return dispatch[ext](path)


# ── 步骤2：结构化 Markdown → Haiku → 解析结果 ────────────────────────────────

def load_prompt_template(prompt_path: Path) -> str:
    """加载课程解析 Prompt 模板。"""
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在：{prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def parse_with_haiku(markdown_content: str, prompt_template: str,
                     client: anthropic.Anthropic) -> str:
    """
    将结构化 Markdown 填入 Prompt，调用 claude-haiku-4-5 提取字段。
    输入已是干净的结构化 Markdown，Haiku 只需做字段映射，成本低且准确。
    """
    prompt = prompt_template.replace("{{课程原始课纲内容}}", markdown_content)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    result = message.content[0].text.strip()
    # 去除模型可能附加的外层 markdown 代码块包装
    if result.startswith("```"):
        lines = result.split("\n")
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        result = "\n".join(lines[start:end]).strip()
    return result


# ── 目录扫描与批处理 ──────────────────────────────────────────────────────────

def scan_course_files(input_dir: Path) -> list:
    """递归扫描目录，返回所有支持格式的课纲文件（排除隐藏/临时文件）。"""
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(input_dir.rglob(f"*{ext}"))
    return sorted(
        f for f in files
        if not f.name.startswith(".") and not f.name.startswith("~")
    )


def process_directory(input_dir: Path, output_dir: Path,
                      prompt_path: Path) -> dict:
    """
    批量处理课纲文件：Python提取结构 → Haiku解析字段 → 保存结果。
    返回 {"processed": int, "failed": int, "output_dir": str}。
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_template = load_prompt_template(prompt_path)
    client = anthropic.Anthropic()

    course_files = scan_course_files(input_dir)
    if not course_files:
        print(f"⚠️  目录中没有找到课纲文件（支持 docx/md）：{input_dir}")
        return {"processed": 0, "failed": 0, "output_dir": str(output_dir)}

    print(f"📋 找到 {len(course_files)} 个课纲文件\n")

    processed, failed = 0, 0

    for course_file in course_files:
        try:
            relative = course_file.relative_to(input_dir)
            display_name = str(relative)
        except ValueError:
            display_name = course_file.name

        print(f"  解析中：{display_name}")

        try:
            # 步骤1：Python提取结构化Markdown
            md_content = read_course_file(course_file)
            if not md_content.strip():
                print(f"  ⚠️  文件内容为空，跳过：{display_name}")
                continue

            # 步骤2：Haiku提取字段
            result = parse_with_haiku(md_content, prompt_template, client)

            output_file = output_dir / (course_file.stem + "_解析结果.md")
            output_file.write_text(result, encoding="utf-8")
            print(f"  ✅ 已保存：{output_file.name}")
            processed += 1

        except Exception as e:
            print(f"  ❌ 失败：{display_name} → {e}")
            failed += 1

    return {"processed": processed, "failed": failed, "output_dir": str(output_dir)}


# ── CLI 入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="课程大纲解析脚本（方案A：Python结构提取 + Haiku字段解析）"
    )
    parser.add_argument("--input",  "-i", type=str, help="课纲文件输入目录")
    parser.add_argument("--output", "-o", type=str, help="解析结果输出目录")
    parser.add_argument("--prompt", "-p", type=str, help="课程解析 Prompt 文件路径")
    args = parser.parse_args()

    script_dir  = Path(__file__).resolve().parent
    program_dir = script_dir.parent.parent   # 06_处理脚本/课纲解析 → program/
    project_dir = program_dir.parent         # program → Agent-work-test/

    input_dir  = Path(args.input)  if args.input  else program_dir / "02_课程大纲库" / "01_原始课纲"
    output_dir = Path(args.output) if args.output else program_dir / "02_课程大纲库" / "02_课纲解析结果"
    prompt_path = Path(args.prompt) if args.prompt else project_dir / "Training" / "dmeo" / "课程解析Prompt.md"

    print(f"\n📂 输入目录：{input_dir}")
    print(f"📂 输出目录：{output_dir}")
    print(f"📄 Prompt：{prompt_path}\n")

    if not input_dir.exists():
        print(f"❌ 输入目录不存在：{input_dir}")
        sys.exit(1)

    if not prompt_path.exists():
        print(f"❌ Prompt 文件不存在：{prompt_path}")
        print("  请通过 --prompt 参数指定正确路径")
        sys.exit(1)

    result = process_directory(input_dir, output_dir, prompt_path)

    print(f"\n✅ 解析完成")
    print(f"   处理文件数：{result['processed']}")
    if result["failed"]:
        print(f"   失败文件数：{result['failed']}")
    print(f"   输出目录：{result['output_dir']}")


if __name__ == "__main__":
    main()
