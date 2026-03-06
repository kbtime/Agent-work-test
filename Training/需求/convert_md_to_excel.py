import os
import re
import pandas as pd
from pathlib import Path

# 定义文件夹路径
input_dir = Path("d:/code/Agent/Training/需求")
output_dir = Path("d:/code/Agent/Training/需求/搜集")

# 确保输出目录存在
output_dir.mkdir(parents=True, exist_ok=True)

def clean_value(text):
    """清理文本：移除填写内容前缀和markdown标记"""
    if not text:
        return ''
    # 移除 "填写内容：" 及其后面的重复内容
    # 先查找 "填写内容：" 的位置，只保留第一次出现之前的内容
    idx = text.find('填写内容：')
    if idx > 0:
        text = text[:idx].strip()
    # 清理markdown分隔符
    text = re.sub(r'---+', '', text).strip()
    # 清理多余的空行
    text = re.sub(r'\n+', '\n', text).strip()
    return text

def parse_markdown_to_dict(md_content):
    """解析Markdown内容，提取关键字段"""
    data = {}

    # 需求标题 - 直接提取 "**需求标题**" 后面到下一个 ** 之间的内容
    match = re.search(r'\*\*需求标题\*\*\s*\n(.+?)(?=\n\*\*|\n---|\n##)', md_content, re.DOTALL)
    if match:
        data['需求标题'] = clean_value(match.group(1))

    # 需求来源部门
    depts = []
    if re.search(r'- \[x\] 销售部', md_content): depts.append('销售部')
    if re.search(r'- \[x\] 客服部', md_content): depts.append('客服部')
    if re.search(r'- \[x\] 运营部', md_content): depts.append('运营部')
    if re.search(r'- \[x\] 人力资源部', md_content): depts.append('人力资源部')
    if re.search(r'- \[x\] 技术部门', md_content): depts.append('技术部门')
    dept_match = re.search(r'- \[ \] 其他：(.+)', md_content)
    if dept_match:
        other = dept_match.group(1).strip()
        if other:
            depts.append(other)
    data['需求来源部门'] = ', '.join(depts)

    # 需求提出人
    name_match = re.search(r'姓名：(.+)', md_content)
    pos_match = re.search(r'岗位：(.+)', md_content)
    data['需求提出人-姓名'] = name_match.group(1).strip() if name_match else ''
    data['需求提出人-岗位'] = pos_match.group(1).strip() if pos_match else ''

    # 涉及岗位/人群
    positions = []
    if re.search(r'- \[x\] 新员工', md_content): positions.append('新员工')
    if re.search(r'- \[x\] 销售人员', md_content): positions.append('销售人员')
    if re.search(r'- \[x\] 客服人员', md_content): positions.append('客服人员')
    if re.search(r'- \[x\] 门店员工', md_content): positions.append('门店员工')
    if re.search(r'- \[x\] 管理层', md_content): positions.append('管理层')
    pos_other = re.search(r'- \[ \] 其他：(.+)', md_content)
    if pos_other:
        other_pos = pos_other.group(1).strip()
        if other_pos:
            positions.append(other_pos)
    data['涉及岗位/人群'] = ', '.join(positions)

    # 预计人数
    count_match = re.search(r'预计人数：(\d+)人', md_content)
    data['预计人数'] = count_match.group(1) if count_match else ''

    # 当前遇到的主要问题
    match = re.search(r'\*\*当前遇到的主要问题\*\*\s*\n(.+?)(?=\n\*\*典型案例|\n---\s*\n\*\*典型案例)', md_content, re.DOTALL)
    if match:
        data['当前遇到的主要问题'] = clean_value(match.group(1))

    # 典型案例
    match = re.search(r'\*\*典型案例（如有）\*\*\s*\n(.+?)(?=\n\*\*问题出现频率|\n---\s*\n\*\*问题出现频率)', md_content, re.DOTALL)
    if match:
        data['典型案例'] = clean_value(match.group(1))

    # 问题出现频率
    freq = []
    if re.search(r'- \[x\] 经常发生', md_content): freq.append('经常发生')
    if re.search(r'- \[x\] 偶尔发生', md_content): freq.append('偶尔发生')
    if re.search(r'- \[x\] 最近开始出现', md_content): freq.append('最近开始出现')
    if re.search(r'- \[x\] 不确定', md_content): freq.append('不确定')
    data['问题出现频率'] = ', '.join(freq)

    # 对业务的影响
    match = re.search(r'\*\*对业务的影响\*\*\s*\n(.+?)(?=\n\*\*希望提升的能力|\n---\s*\n\*\*希望提升)', md_content, re.DOTALL)
    if match:
        data['对业务的影响'] = clean_value(match.group(1))

    # 希望提升的能力
    abilities = []
    if re.search(r'- \[x\] 销售技巧', md_content): abilities.append('销售技巧')
    if re.search(r'- \[x\] 客户沟通', md_content): abilities.append('客户沟通')
    if re.search(r'- \[x\] 产品知识', md_content): abilities.append('产品知识')
    if re.search(r'- \[x\] 客户服务', md_content): abilities.append('客户服务')
    if re.search(r'- \[x\] 投诉处理', md_content): abilities.append('投诉处理')
    if re.search(r'- \[x\] 团队管理', md_content): abilities.append('团队管理')
    if re.search(r'- \[x\] 沟通表达', md_content): abilities.append('沟通表达')
    if re.search(r'- \[x\] 工作效率', md_content): abilities.append('工作效率')
    data['希望提升的能力'] = ', '.join(abilities)

    # 希望解决的具体问题
    match = re.search(r'\*\*希望解决的具体问题\*\*\s*\n(.+?)(?=\n\*\*期望培训形式|\n---\s*\n\*\*期望培训形式)', md_content, re.DOTALL)
    if match:
        data['希望解决的具体问题'] = clean_value(match.group(1))

    # 期望培训形式
    forms = []
    if re.search(r'- \[x\] 线下培训', md_content): forms.append('线下培训')
    if re.search(r'- \[x\] 线上课程', md_content): forms.append('线上课程')
    if re.search(r'- \[x\] 工作坊 / 研讨会', md_content): forms.append('工作坊/研讨会')
    if re.search(r'- \[x\] 案例分享', md_content): forms.append('案例分享')
    if re.search(r'- \[x\] 实战演练', md_content): forms.append('实战演练')
    data['期望培训形式'] = ', '.join(forms)

    # 期望培训时间
    time_pref = []
    if re.search(r'- \[x\] 尽快安排', md_content): time_pref.append('尽快安排')
    if re.search(r'- \[x\] 本季度', md_content): time_pref.append('本季度')
    if re.search(r'- \[x\] 本年度', md_content): time_pref.append('本年度')
    if re.search(r'- \[x\] 时间不紧急', md_content): time_pref.append('时间不紧急')
    data['期望培训时间'] = ', '.join(time_pref)

    # 是否已有推荐课程或讲师
    match = re.search(r'\*\*是否已有推荐课程或讲师\*\*\s*\n(.+?)(?=\n\*\*其他补充说明|\n---\s*\n\*\*其他补充说明)', md_content, re.DOTALL)
    if match:
        data['是否已有推荐课程或讲师'] = clean_value(match.group(1))

    # 其他补充说明
    match = re.search(r'\*\*其他补充说明\*\*\s*\n(.+?)(?=\n---\s*\n## 五|\n## 五)', md_content, re.DOTALL)
    if match:
        data['其他补充说明'] = clean_value(match.group(1))

    # 提交日期
    date_match = re.search(r'提交日期：(\d{4}-\d{2}-\d{2})', md_content)
    data['提交日期'] = date_match.group(1) if date_match else ''

    # 负责人确认
    resp_match = re.search(r'负责人确认：(.+)', md_content)
    data['负责人确认'] = resp_match.group(1).strip() if resp_match else ''

    return data

# 定义标准的Excel格式（字段名称列表，按照标准模板的顺序）
field_columns = [
    ('一、需求基本信息', ''),
    ('需求标题', '需求标题'),
    ('需求来源部门', '需求来源部门'),
    ('需求提出人-姓名', '需求提出人-姓名'),
    ('需求提出人-岗位', '需求提出人-岗位'),
    ('涉及岗位/人群', '涉及岗位/人群'),
    ('预计人数', '预计人数'),
    ('', ''),
    ('二、问题描述', ''),
    ('当前遇到的主要问题', '当前遇到的主要问题'),
    ('典型案例', '典型案例'),
    ('问题出现频率', '问题出现频率'),
    ('对业务的影响', '对业务的影响'),
    ('', ''),
    ('三、培训期望', ''),
    ('希望提升的能力', '希望提升的能力'),
    ('希望解决的具体问题', '希望解决的具体问题'),
    ('期望培训形式', '期望培训形式'),
    ('期望培训时间', '期望培训时间'),
    ('', ''),
    ('四、补充信息（可选）', ''),
    ('是否已有推荐课程或讲师', '是否已有推荐课程或讲师'),
    ('其他补充说明', '其他补充说明'),
    ('', ''),
    ('五、提交信息', ''),
    ('提交日期', '提交日期'),
    ('负责人确认', '负责人确认'),
]

# 获取所有MD文件
md_files = sorted(input_dir.glob("*.md"))
print(f"找到 {len(md_files)} 个MD文件")

# 先清除旧的Excel文件
for f in output_dir.glob("*.xlsx"):
    f.unlink()

# 解析并保存每个文件为单独的Excel
for md_file in md_files:
    print(f"处理: {md_file.name}")
    content = md_file.read_text(encoding='utf-8')
    data = parse_markdown_to_dict(content)

    # 创建两列的DataFrame（按照标准格式）
    rows = []
    for field_label, data_key in field_columns:
        value = data.get(data_key, '') if data_key else ''
        rows.append([field_label, value])

    df = pd.DataFrame(rows)

    # 保存到Excel (文件名去掉.md后缀)
    output_file = output_dir / (md_file.stem + ".xlsx")
    df.to_excel(output_file, index=False, header=False, engine='openpyxl')

print(f"\n完成！已生成 {len(md_files)} 个Excel文件到: {output_dir}")
