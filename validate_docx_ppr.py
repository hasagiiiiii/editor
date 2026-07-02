import zipfile
from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

with zipfile.ZipFile('d:/editor/backend/storage/edited/Tài_Liệu_Thiết_Kế_Chi_Tiết_-_Nâng_Cấp_Repeater_Component_(1).docx', 'r') as z:
    xml_data = z.read('word/document.xml')

root = etree.fromstring(xml_data)

errors = []
for p in root.iter(f"{W}p"):
    p_pr_count = 0
    for i, child in enumerate(p):
        if child.tag == f"{W}pPr":
            p_pr_count += 1
            if i != 0:
                errors.append(f"Error: pPr is at index {i} instead of 0 in a paragraph.")
    if p_pr_count > 1:
        errors.append(f"Error: Paragraph has {p_pr_count} pPr elements!")

print(f"Total pPr errors found: {len(errors)}")
if errors:
    for e in errors[:10]:
        print(e)
