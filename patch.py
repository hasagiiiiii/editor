import re

with open('d:/editor/backend/docx_xml_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace _replace_paragraph_text signature
old_sig = '''    def _replace_paragraph_text(
        self, p_elem: etree._Element, new_text: str
    ) -> None:'''
new_sig = '''    def _replace_paragraph_text(
        self, p_elem: etree._Element, new_text: str, doc
    ) -> None:'''

content = content.replace(old_sig, new_sig)

# Replace _replace_paragraph_text body (from parts = new_text.split("**") to the end of the method)
old_body = '''        # Phân tích cú pháp in đậm ** để chèn thành các w:r khác nhau
        parts = new_text.split("**")
        for idx, part in enumerate(parts):
            if not part:
                continue
            is_bold = (idx % 2 == 1)
            
            r_segment = etree.SubElement(p_elem, f"{W}r")
            segment_r_pr = None
            if first_r_pr is not None:
                segment_r_pr = copy.deepcopy(first_r_pr)
            
            if is_bold:
                if segment_r_pr is None:
                    segment_r_pr = etree.Element(f"{W}rPr")
                for b_tag in (f"{W}b", f"{W}bCs"):
                    if segment_r_pr.find(b_tag) is None:
                        etree.SubElement(segment_r_pr, b_tag)
                        
            if segment_r_pr is not None and len(segment_r_pr) > 0:
                r_segment.append(segment_r_pr)
                
            t_segment = etree.SubElement(r_segment, f"{W}t")
            t_segment.text = part
            if part[0] == " " or part[-1] == " ":
                t_segment.set(self._XML_SPACE, "preserve")'''

new_body = '''        from docx.text.paragraph import Paragraph
        p = Paragraph(p_elem, doc)

        # Phân tích cú pháp in đậm ** để chèn thành các w:r khác nhau
        parts = new_text.split("**")
        for idx, part in enumerate(parts):
            if not part:
                continue
            is_bold = (idx % 2 == 1)
            
            run = p.add_run(part)
            if first_r_pr is not None:
                rPr = run._r.get_or_add_rPr()
                run._r.remove(rPr)
                run._r.append(copy.deepcopy(first_r_pr))
            if is_bold:
                run.bold = True'''

content = content.replace(old_body, new_body)

# Replace merge_edited_text insertion logic
old_insertion = '''                    # Tạo đoạn văn mới w:p với nsmap giống hệt phần tử neo để tránh lỗi namespace trong Word
                    new_p = etree.Element(f"{W}p", nsmap=anchor_elem.nsmap)
                    
                    # Sao chép định dạng paragraph w:pPr từ đoạn neo gốc
                    orig_elem = p_index[target_id]
                    orig_p_pr = orig_elem.find(f"{W}pPr")
                    if orig_p_pr is not None:
                        new_p.append(copy.deepcopy(orig_p_pr))

                    # Lấy định dạng run style đầu tiên từ đoạn gốc để kế thừa (loại bỏ in đậm mặc định)
                    first_r_pr = None
                    for r_el in orig_elem.iter(f"{W}r"):
                        r_pr = r_el.find(f"{W}rPr")
                        if r_pr is not None:
                            first_r_pr = copy.deepcopy(r_pr)
                            for b_tag in (f"{W}b", f"{W}bCs"):
                                b_el = first_r_pr.find(b_tag)
                                if b_el is not None:
                                    first_r_pr.remove(b_el)
                            break

                    # Phân tích và tạo các run thường & run in đậm dựa trên cú pháp **
                    parts = new_text.split("**")
                    for idx, part in enumerate(parts):
                        if not part:
                            continue
                        is_bold = (idx % 2 == 1)
                        
                        r_segment = etree.SubElement(new_p, f"{W}r")
                        segment_r_pr = None
                        if first_r_pr is not None:
                            segment_r_pr = copy.deepcopy(first_r_pr)
                        
                        if is_bold:
                            if segment_r_pr is None:
                                segment_r_pr = etree.Element(f"{W}rPr")
                            for b_tag in (f"{W}b", f"{W}bCs"):
                                if segment_r_pr.find(b_tag) is None:
                                    etree.SubElement(segment_r_pr, b_tag)
                                    
                        if segment_r_pr is not None and len(segment_r_pr) > 0:
                            r_segment.append(segment_r_pr)
                            
                        t_segment = etree.SubElement(r_segment, f"{W}t")
                        t_segment.text = part
                        if part[0] == " " or part[-1] == " ":
                            t_segment.set(self._XML_SPACE, "preserve")

                    # Chèn vào XML sau phần tử neo hiện tại
                    idx_pos = parent.index(anchor_elem)
                    parent.insert(idx_pos + 1, new_p)

                    # Cập nhật neo để lượt chèn tiếp theo nằm sau đoạn mới này
                    anchors[target_id] = new_p
                    applied_count += 1
                else:
                    # Logic sửa đổi hoặc xóa đoạn văn gốc
                    if key not in p_index:
                        continue
                    p_elem = p_index[key]

                    if new_text == "":
                        # Xóa đoạn văn
                        parent = p_elem.getparent()
                        if parent is not None:
                            parent.remove(p_elem)
                        # Xóa khỏi danh sách neo để không thể chèn sau nó nữa
                        if key in anchors:
                            del anchors[key]
                        applied_count += 1
                    else:
                        # Thay thế văn bản
                        self._replace_paragraph_text(p_elem, new_text)
                        applied_count += 1'''

new_insertion = '''                    from docx.oxml.shared import OxmlElement
                    from docx.text.paragraph import Paragraph

                    # Tạo đoạn văn mới w:p
                    new_p = OxmlElement('w:p')
                    
                    # Sao chép định dạng paragraph w:pPr từ đoạn neo gốc
                    orig_elem = p_index[target_id]
                    orig_p_pr = orig_elem.find(f"{W}pPr")
                    if orig_p_pr is not None:
                        new_p.append(copy.deepcopy(orig_p_pr))

                    # Chèn vào XML sau phần tử neo hiện tại
                    idx_pos = parent.index(anchor_elem)
                    parent.insert(idx_pos + 1, new_p)

                    # Lấy định dạng run style đầu tiên từ đoạn gốc để kế thừa (loại bỏ in đậm mặc định)
                    first_r_pr = None
                    for r_el in orig_elem.iter(f"{W}r"):
                        r_pr = r_el.find(f"{W}rPr")
                        if r_pr is not None:
                            first_r_pr = copy.deepcopy(r_pr)
                            for b_tag in (f"{W}b", f"{W}bCs"):
                                b_el = first_r_pr.find(b_tag)
                                if b_el is not None:
                                    first_r_pr.remove(b_el)
                            break

                    p = Paragraph(new_p, doc)

                    # Phân tích và tạo các run thường & run in đậm dựa trên cú pháp **
                    text_parts = new_text.split("**")
                    for idx, part in enumerate(text_parts):
                        if not part:
                            continue
                        is_bold = (idx % 2 == 1)
                        run = p.add_run(part)
                        
                        if first_r_pr is not None:
                            rPr = run._r.get_or_add_rPr()
                            run._r.remove(rPr)
                            run._r.append(copy.deepcopy(first_r_pr))
                            
                        if is_bold:
                            run.bold = True

                    # Cập nhật neo để lượt chèn tiếp theo nằm sau đoạn mới này
                    anchors[target_id] = new_p
                    applied_count += 1
                else:
                    # Logic sửa đổi hoặc xóa đoạn văn gốc
                    if key not in p_index:
                        continue
                    p_elem = p_index[key]

                    if new_text == "":
                        # Xóa đoạn văn
                        parent = p_elem.getparent()
                        if parent is not None:
                            parent.remove(p_elem)
                        # Xóa khỏi danh sách neo để không thể chèn sau nó nữa
                        if key in anchors:
                            del anchors[key]
                        applied_count += 1
                    else:
                        # Thay thế văn bản
                        self._replace_paragraph_text(p_elem, new_text, doc)
                        applied_count += 1'''

content = content.replace(old_insertion, new_insertion)

with open('d:/editor/backend/docx_xml_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch applied")
