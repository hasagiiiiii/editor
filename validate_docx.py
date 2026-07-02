import zipfile
from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

with zipfile.ZipFile('d:/editor/backend/storage/edited/Tài_Liệu_Thiết_Kế_Chi_Tiết_-_Nâng_Cấp_Repeater_Component_(1).docx', 'r') as z:
    xml_data = z.read('word/document.xml')

root = etree.fromstring(xml_data)

errors = []
for r in root.iter(f"{W}r"):
    r_pr_count = 0
    for i, child in enumerate(r):
        if child.tag == f"{W}rPr":
            r_pr_count += 1
            if i != 0:
                errors.append(f"Error: rPr is at index {i} instead of 0 in a run. Run text: {''.join(t.text for t in r.findall(f'{W}t') if t.text)}")
    if r_pr_count > 1:
        errors.append(f"Error: Run has {r_pr_count} rPr elements!")

print(f"Total errors found: {len(errors)}")
if errors:
    for e in errors[:10]:
        print(e)
