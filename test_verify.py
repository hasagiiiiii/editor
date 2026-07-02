from docx import Document
from lxml import etree

doc = Document('d:/editor/test_output.docx')
# find our test paragraph
p = None
for paragraph in doc.paragraphs:
    if 'test' in paragraph.text:
        p = paragraph
        break

if p:
    xml_str = p._element.xml
    print(xml_str)
else:
    print("Not found")
