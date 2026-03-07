#!/usr/bin/env python3
"""
课程能力构建器（course_builder）
将课程解析结果（*_解析结果.md）转换为标准课程能力对象。

每门课程生成四个文件：
  课程结构卡片.md   基本信息 + 适用范围 + 模块结构的可读摘要卡片
  课程摘要.md       摘要文字和检索关键词
  能力标签.json     含课程ID的完整能力标签对象
  讲师版本映射.json  讲师姓名和版本记录

还会更新（或创建）课程能力汇总库根目录的课程索引.md。

用法：
    python course_builder.py [--input <输入目录>] [--output <输出目录>]

默认路径（相对于 program/ 目录）：
    输入：02_课程大纲库/02_课纲解析结果/
    输出：02_课程大纲库/03_课程能力汇总库/
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


# ── 解析解析结果 MD ────────────────────────────────────────────────────────────

def extract_json_block(text: str) -> dict:
    """从 Markdown 文本末尾提取第一个 ```json ... ``` 代码块并解析。"""
    pattern = r"```json\s*([\s\S]*?)```"
    matches = re.findall(pattern, text)
    if not matches:
        raise ValueError("未找到 JSON 代码块（```json ... ```）")
    # 取最后一个 JSON 块（解析结果文件末尾的能力标签）
    raw = matches[-1].strip()
    return json.loads(raw)


def extract_section(text: str, section_name: str) -> str:
    """
    从 Markdown 正文中提取指定二级标题（## section_name）下的内容。
    返回该段落文本（不含标题行），遇到下一个二级标题或文件末尾停止。
    """
    pattern = rf"##\s+{re.escape(section_name)}\s*\n([\s\S]*?)(?=\n##\s|\Z)"
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def extract_field(text: str, field_name: str) -> str:
    """从列表行中提取 **字段名**：值 格式的内容（单行值）。"""
    pattern = rf"\*\*{re.escape(field_name)}\*\*[：:]\s*(.+)"
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


def parse_result_file(path: Path) -> dict:
    """
    解析一个 *_解析结果.md 文件。
    返回包含 json_data（能力标签 dict）和 sections（各段文本）的字典。
    """
    content = path.read_text(encoding="utf-8")
    json_data = extract_json_block(content)

    # 去掉末尾 JSON 块，仅保留 Markdown 正文部分
    md_body = re.sub(r"```json[\s\S]*?```", "", content).strip()

    sections = {
        "基本信息": extract_section(md_body, "基本信息"),
        "适用范围": extract_section(md_body, "适用范围"),
        "问题与能力": extract_section(md_body, "问题与能力"),
        "课程结构": extract_section(md_body, "课程结构"),
        "摘要与检索": extract_section(md_body, "摘要与检索"),
    }

    # 从基本信息中提取讲师姓名
    instructor = extract_field(sections["基本信息"], "讲师姓名")

    # 从摘要与检索中提取摘要文字和关键词
    summary_text = extract_field(sections["摘要与检索"], "课程摘要")
    keywords_raw = extract_field(sections["摘要与检索"], "需求关键词")
    keywords = [k.strip() for k in keywords_raw.split("，") if k.strip()] if keywords_raw else []
    # 也尝试顿号分隔
    if len(keywords) == 1 and "," in keywords[0]:
        keywords = [k.strip() for k in keywords[0].split(",") if k.strip()]

    return {
        "json_data": json_data,
        "sections": sections,
        "instructor": instructor,
        "summary_text": summary_text,
        "keywords": keywords,
        "course_name": json_data.get("标准课程名称", path.stem.replace("_解析结果", "")),
    }


# ── 课程ID 分配 ────────────────────────────────────────────────────────────────

def load_existing_id_map(output_dir: Path) -> dict:
    """
    扫描输出目录，构建 {课程名称: 课程ID} 映射，
    同时记录当前最大编号以便新增时递增。
    """
    id_map = {}
    max_num = 0

    if not output_dir.exists():
        return id_map, max_num

    for folder in output_dir.iterdir():
        if not folder.is_dir():
            continue
        m = re.match(r"^(COURSE-(\d+))_(.+)$", folder.name)
        if m:
            course_id = m.group(1)
            num = int(m.group(2))
            course_name = m.group(3)
            id_map[course_name] = course_id
            if num > max_num:
                max_num = num

    return id_map, max_num


def assign_course_id(course_name: str, id_map: dict, max_num_ref: list) -> str:
    """
    分配课程ID：
    - 若课程名称已在 id_map 中，复用已有ID
    - 否则新建递增ID，并更新 id_map 和 max_num_ref[0]
    """
    if course_name in id_map:
        return id_map[course_name]

    max_num_ref[0] += 1
    new_id = f"COURSE-{max_num_ref[0]:03d}"
    id_map[course_name] = new_id
    return new_id


# ── 生成四个输出文件 ───────────────────────────────────────────────────────────

def build_structure_card(parsed: dict, course_id: str) -> str:
    """生成课程结构卡片.md。"""
    s = parsed["sections"]
    name = parsed["course_name"]
    instructor = parsed["instructor"]

    lines = [
        f"# 课程结构卡片",
        f"",
        f"**课程ID**：{course_id}",
        f"**课程名称**：{name}",
        f"**主讲讲师**：{instructor}" if instructor else "",
        f"",
        f"---",
        f"",
    ]

    if s["基本信息"]:
        lines += ["## 基本信息", "", s["基本信息"], ""]

    if s["适用范围"]:
        lines += ["## 适用范围", "", s["适用范围"], ""]

    if s["课程结构"]:
        lines += ["## 课程结构", "", s["课程结构"], ""]

    return "\n".join(l for l in lines if l is not None)


def build_summary(parsed: dict, course_id: str) -> str:
    """生成课程摘要.md。"""
    name = parsed["course_name"]
    summary = parsed["summary_text"] or "（暂无摘要）"
    keywords = parsed["keywords"]

    kw_str = "、".join(keywords) if keywords else "（暂无关键词）"

    return f"""# 课程摘要

**课程ID**：{course_id}
**课程名称**：{name}

## 摘要

{summary}

## 检索关键词

{kw_str}
"""


def build_ability_tags(parsed: dict, course_id: str) -> dict:
    """生成能力标签 JSON 对象（注入课程ID）。"""
    data = dict(parsed["json_data"])
    data["课程ID"] = course_id
    # 确保字段顺序友好
    ordered = {"课程ID": course_id}
    for key, val in data.items():
        if key != "课程ID":
            ordered[key] = val
    return ordered


def build_instructor_map(parsed: dict, course_id: str) -> dict:
    """生成讲师版本映射 JSON。"""
    return {
        "课程ID": course_id,
        "课程名称": parsed["course_name"],
        "版本记录": [
            {
                "版本号": "v1.0",
                "讲师": parsed["instructor"] or "未知",
                "创建日期": date.today().isoformat(),
                "备注": "初始版本（由 course_builder 自动生成）"
            }
        ]
    }


# ── 课程索引 ───────────────────────────────────────────────────────────────────

def update_course_index(output_dir: Path, index_entries: list[dict]):
    """
    更新（或创建）课程索引.md。
    index_entries: [{course_id, course_name, instructor, keywords}]
    """
    lines = [
        "# 课程能力汇总库 — 课程索引",
        "",
        f"更新日期：{date.today().isoformat()}",
        "",
        "| 课程ID | 课程名称 | 主讲讲师 | 关键词 |",
        "|--------|----------|----------|--------|",
    ]
    for e in sorted(index_entries, key=lambda x: x["course_id"]):
        kw = "、".join(e["keywords"][:4]) if e["keywords"] else "—"
        lines.append(
            f"| {e['course_id']} | {e['course_name']} | {e['instructor'] or '—'} | {kw} |"
        )

    index_path = output_dir / "课程索引.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index_path


# ── 主流程 ─────────────────────────────────────────────────────────────────────

def process_all(input_dir: Path, output_dir: Path) -> dict:
    """
    批量处理解析结果文件，生成课程能力对象。
    返回 {"processed": int, "failed": int, "output_dir": str}。
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    result_files = sorted(input_dir.glob("*_解析结果.md"))
    if not result_files:
        print(f"⚠️  目录中没有找到解析结果文件（*_解析结果.md）：{input_dir}")
        return {"processed": 0, "failed": 0, "output_dir": str(output_dir)}

    print(f"📋 找到 {len(result_files)} 个解析结果文件\n")

    id_map, max_num = load_existing_id_map(output_dir)
    max_num_ref = [max_num]  # 用列表包装以便在函数中修改

    processed, failed = 0, 0
    index_entries = []

    for result_file in result_files:
        print(f"  处理中：{result_file.name}")
        try:
            parsed = parse_result_file(result_file)
            course_name = parsed["course_name"]
            course_id = assign_course_id(course_name, id_map, max_num_ref)

            folder_name = f"{course_id}_{course_name}"
            course_dir = output_dir / folder_name
            course_dir.mkdir(parents=True, exist_ok=True)

            # 生成四个文件
            (course_dir / "课程结构卡片.md").write_text(
                build_structure_card(parsed, course_id), encoding="utf-8"
            )
            (course_dir / "课程摘要.md").write_text(
                build_summary(parsed, course_id), encoding="utf-8"
            )
            (course_dir / "能力标签.json").write_text(
                json.dumps(build_ability_tags(parsed, course_id),
                           ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            (course_dir / "讲师版本映射.json").write_text(
                json.dumps(build_instructor_map(parsed, course_id),
                           ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            index_entries.append({
                "course_id": course_id,
                "course_name": course_name,
                "instructor": parsed["instructor"],
                "keywords": parsed["keywords"],
            })

            print(f"  ✅ 已生成：{folder_name}/")
            processed += 1

        except Exception as e:
            print(f"  ❌ 失败：{result_file.name} → {e}")
            failed += 1

    # 更新课程索引
    if index_entries:
        index_path = update_course_index(output_dir, index_entries)
        print(f"\n📑 已更新课程索引：{index_path.name}")

    return {"processed": processed, "failed": failed, "output_dir": str(output_dir)}


# ── CLI 入口 ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="课程能力构建器：将课程解析结果转换为标准课程能力对象"
    )
    parser.add_argument("--input",  "-i", type=str, help="解析结果输入目录")
    parser.add_argument("--output", "-o", type=str, help="课程能力输出目录")
    args = parser.parse_args()

    script_dir  = Path(__file__).resolve().parent
    program_dir = script_dir.parent.parent   # 06_处理脚本/课纲解析 → program/

    input_dir  = Path(args.input)  if args.input  else program_dir / "02_课程大纲库" / "02_课纲解析结果"
    output_dir = Path(args.output) if args.output else program_dir / "02_课程大纲库" / "03_课程能力汇总库"

    print(f"\n📂 输入目录：{input_dir}")
    print(f"📂 输出目录：{output_dir}\n")

    if not input_dir.exists():
        print(f"❌ 输入目录不存在：{input_dir}")
        sys.exit(1)

    result = process_all(input_dir, output_dir)

    print(f"\n✅ 构建完成")
    print(f"   处理文件数：{result['processed']}")
    if result["failed"]:
        print(f"   失败文件数：{result['failed']}")
    print(f"   输出目录：{result['output_dir']}")


if __name__ == "__main__":
    main()
