from lxml import etree
from docx.text.paragraph import Paragraph
from docx import Document

doc = Document()
xml = b'<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:r><w:t>Hello</w:t></w:r></w:p>'
p_elem = etree.fromstring(xml)

try:
    p = Paragraph(p_elem, doc)
    run = p.add_run('World')
    print('Success:', p_elem.tag)
except Exception as e:
    print('Error:', e)
