with open('d:/editor/backend/docx_xml_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("run._r.append(copy.deepcopy(first_r_pr))", "run._r.insert(0, copy.deepcopy(first_r_pr))")

with open('d:/editor/backend/docx_xml_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch 2 applied")
