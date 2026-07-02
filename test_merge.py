import sys
from pathlib import Path
from docx import Document

sys.path.insert(0, str(Path('d:/editor/backend')))
from docx_xml_processor import DocxXmlProcessor

doc = Document()
doc.add_paragraph('This is a test paragraph to check bolding logic.')
doc.save('d:/editor/test_input.docx')

processor = DocxXmlProcessor()
edited_json = {
    'p_1': 'This is a **test** paragraph to check **bolding** logic.'
}
processor.merge_edited_text('d:/editor/test_input.docx', edited_json, 'd:/editor/test_output.docx')
print("Merge complete")
