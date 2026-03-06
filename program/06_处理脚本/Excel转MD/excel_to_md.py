#!/usr/bin/env python3
"""
Excel 转 Markdown 转换脚本
将培训需求 Excel 文件转换为 Markdown 格式，供后续 AI 提取结构化需求使用。

用法：
    python excel_to_md.py --input <输入目录> --output <输出目录>

默认路径（相对于脚本所在位置向上两级的 program 目录）：
    输入：01_培训需求库/01_原始Excel/
    输出：01_培训需求库/02_MD转换结果/
"""

import argparse
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("❌ 缺少依赖：openpyxl")
    print("请在 venv 中安装：pip install openpyxl")
    sys.exit(1)


def excel_to_markdown(excel_path: Path) -> str:
    """
    将单个 Excel 文件转换为 Markdown 文本。
    支持两种格式：
    1. 标准两列格式（字段名 | 字段值）
    2. 表头行格式（第一行为字段名，后续行为数据行）
    """
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active

    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell).strip() if cell is not None else "" for cell in row])

    if not rows:
        return f"# {excel_path.stem}\n\n（文件为空）\n"

    md_lines = [f"# 培训需求表：{excel_path.stem}", ""]

    # 判断格式类型
    first_row = rows[0]
    non_empty_first = [c for c in first_row if c and c != "None"]

    # 如果第一列有多行且第二列有值 → 两列键值对格式
    if len(first_row) >= 2:
        # 检查是否为键值对格式（Section headers + key-value rows）
        section_keywords = ["需求基本信息", "问题描述", "培训期望", "补充信息", "提交信息"]
        is_key_value = any(
            any(kw in str(row[0]) for kw in section_keywords)
            for row in rows[:10]
            if row[0]
        )

        if is_key_value:
            md_lines += _parse_key_value_format(rows)
        else:
            # 表头行格式：第一行是字段名
            md_lines += _parse_header_row_format(rows)
    else:
        # 单列格式，直接输出
        for row in rows:
            md_lines.append(row[0] if row else "")

    return "\n".join(md_lines) + "\n"


def _parse_key_value_format(rows: list) -> list:
    """解析两列键值对格式的 Excel（字段名 | 字段值）"""
    lines = []
    section_keywords = ["需求基本信息", "问题描述", "培训期望", "补充信息", "提交信息"]

    for row in rows:
        if len(row) < 2:
            continue

        key = row[0].strip()
        value = row[1].strip() if len(row) > 1 else ""

        if not key or key == "None":
            continue

        # 章节标题
        if any(kw in key for kw in section_keywords) and not value:
            lines.append(f"\n## {key}\n")
        else:
            lines.append(f"**{key}**：{value}")

    return lines


def _parse_header_row_format(rows: list) -> list:
    """解析表头行格式（第一行字段名，后续为数据行）"""
    lines = []
    if not rows:
        return lines

    headers = rows[0]
    data_rows = rows[1:]

    # 过滤掉全空行
    data_rows = [r for r in data_rows if any(c and c != "None" for c in r)]

    if not data_rows:
        lines.append("（无数据行）")
        return lines

    for i, row in enumerate(data_rows, 1):
        lines.append(f"\n## 需求记录 {i}\n")
        for j, header in enumerate(headers):
            if not header or header == "None":
                continue
            value = row[j] if j < len(row) else ""
            if value and value != "None":
                lines.append(f"**{header}**：{value}")
        lines.append("")

    return lines


def convert_directory(input_dir: Path, output_dir: Path) -> dict:
    """
    批量转换目录中的所有 Excel 文件。
    返回处理结果统计。
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    excel_files = list(input_dir.glob("*.xlsx")) + list(input_dir.glob("*.xls"))

    if not excel_files:
        print(f"⚠️  目录中没有找到 Excel 文件：{input_dir}")
        return {"processed": 0, "failed": 0, "output_dir": str(output_dir)}

    processed = 0
    failed = 0

    for excel_file in sorted(excel_files):
        try:
            print(f"  转换中：{excel_file.name}")
            md_content = excel_to_markdown(excel_file)

            output_file = output_dir / (excel_file.stem + ".md")
            output_file.write_text(md_content, encoding="utf-8")
            print(f"  ✅ 已保存：{output_file.name}")
            processed += 1
        except Exception as e:
            print(f"  ❌ 失败：{excel_file.name} → {e}")
            failed += 1

    return {
        "processed": processed,
        "failed": failed,
        "output_dir": str(output_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="将培训需求 Excel 文件批量转换为 Markdown")
    parser.add_argument("--input", "-i", type=str, help="Excel 文件输入目录")
    parser.add_argument("--output", "-o", type=str, help="Markdown 文件输出目录")

    args = parser.parse_args()

    # 默认路径：相对于 program 目录
    script_dir = Path(__file__).resolve().parent
    program_dir = script_dir.parent.parent  # 06_处理脚本/Excel转MD → program

    input_dir = Path(args.input) if args.input else program_dir / "01_培训需求库" / "01_原始Excel"
    output_dir = Path(args.output) if args.output else program_dir / "01_培训需求库" / "02_MD转换结果"

    print(f"\n📂 输入目录：{input_dir}")
    print(f"📂 输出目录：{output_dir}\n")

    if not input_dir.exists():
        print(f"❌ 输入目录不存在：{input_dir}")
        sys.exit(1)

    result = convert_directory(input_dir, output_dir)

    print(f"\n✅ 转换完成")
    print(f"   处理文件数：{result['processed']}")
    if result['failed']:
        print(f"   失败文件数：{result['failed']}")
    print(f"   输出目录：{result['output_dir']}")


if __name__ == "__main__":
    main()
