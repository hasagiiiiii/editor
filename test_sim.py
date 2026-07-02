import sys
from pathlib import Path
from docx import Document

sys.path.insert(0, str(Path('d:/editor/backend')))
from docx_xml_processor import DocxXmlProcessor

uploads_dir = Path('d:/editor/backend/storage/uploads')
files = list(uploads_dir.glob('*.docx'))
original_file = files[-1]
edited_file = Path('d:/editor/test_simulate_edit.docx')

processor = DocxXmlProcessor()
data = processor.extract_paragraphs_with_ids(str(original_file))
paragraphs = data['paragraphs']

# Chỉnh sửa đoạn văn có nội dung để test
first_pid = None
for pid, item in paragraphs.items():
    if item.get('text', '').strip():
        first_pid = pid
        break
if not first_pid:
    first_pid = list(paragraphs.keys())[0]

edited_json = {
    first_pid: paragraphs[first_pid]['text'] + ' (Edited by Script)'
}

try:
    processor.merge_edited_text(str(original_file), edited_json, str(edited_file))
    log_text = f"Merged successfully for {first_pid}\n"
except Exception as e:
    log_text = f"Merge failed: {e}\n"

with open('d:/editor/test_log.txt', 'w', encoding='utf-8') as f:
    f.write(log_text)

# Kiểm tra xml sinh ra
try:
    import zipfile
    with zipfile.ZipFile(str(edited_file), 'r') as z:
        xml_data = z.read('word/document.xml')
    with open('d:/editor/test_xml_out.xml', 'wb') as f:
        f.write(xml_data)
except Exception as e:
    pass
