"""
docx_xml_processor.py

Module xử lý file .docx bằng can thiệp trực tiếp vào cấu trúc XML.
Sử dụng python-docx cho I/O file và lxml cho thao tác XML,
phục vụ cho ứng dụng chỉnh sửa văn bản bằng AI.

Cách dùng:
    processor = DocxXmlProcessor()

    # Bước 1: Trích xuất đoạn văn kèm ID
    paragraphs = processor.extract_paragraphs_with_ids("input.docx")
    # => {"p_1": "Nội dung đoạn 1", "p_2": "Nội dung đoạn 2", ...}

    # Bước 2: Gửi cho AI chỉnh sửa, nhận lại dict đã sửa
    edited = {"p_1": "Nội dung mới đoạn 1", "p_2": "Nội dung mới đoạn 2"}

    # Bước 3: Gộp nội dung đã sửa vào file gốc
    processor.merge_edited_text("input.docx", edited, "output.docx")

Dependencies:
    pip install python-docx lxml
"""

from __future__ import annotations

import copy
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from docx import Document
from lxml import etree

__all__ = ["DocxXmlProcessor"]

logger = logging.getLogger(__name__)


class DocxXmlProcessor:
    """
    Xử lý file .docx bằng can thiệp trực tiếp vào cấu trúc XML.

    Cung cấp hai phương thức chính:
      - extract_paragraphs_with_ids: Trích xuất nội dung từng đoạn văn kèm ID.
      - merge_edited_text: Ghi đè nội dung đã chỉnh sửa vào file gốc,
        giữ nguyên định dạng đoạn (w:pPr) và định dạng ký tự (w:rPr).
    """

    # ── OOXML Namespaces ────────────────────────────────────────────
    _W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    _W = f"{{{_W_NS}}}"
    _XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

    # ================================================================
    #  INTERNAL HELPERS
    # ================================================================

    def _is_toc_paragraph(self, p_elem: etree._Element) -> bool:
        """
        Kiểm tra xem đoạn văn có thuộc cấu trúc Mục lục (TOC) hay không.

        Nhận diện qua 5 dấu hiệu:
          1. Paragraph style bắt đầu bằng "TOC" (TOC1, TOC2, TOCHeading, ...).
          2. Nằm trong w:sdt có docPartGallery = "Table of Contents".
          3. Chứa w:instrText có chuỗi "TOC".
          4. Chứa w:fldSimple con có w:instr chứa "TOC".
          5. Phần tử cha là w:fldSimple với w:instr chứa "TOC".
        """
        W = self._W

        # 1. Kiểm tra paragraph style
        p_pr = p_elem.find(f"{W}pPr")
        if p_pr is not None:
            p_style = p_pr.find(f"{W}pStyle")
            if p_style is not None:
                style_val = p_style.get(f"{W}val", "")
                if style_val.upper().startswith("TOC"):
                    return True

        # 2. Kiểm tra tổ tiên w:sdt (Structured Document Tag) cho TOC
        ancestor = p_elem.getparent()
        while ancestor is not None:
            if ancestor.tag == f"{W}sdt":
                sdt_pr = ancestor.find(f"{W}sdtPr")
                if sdt_pr is not None:
                    doc_part = sdt_pr.find(f"{W}docPartObj")
                    if doc_part is not None:
                        gallery = doc_part.find(f"{W}docPartGallery")
                        if gallery is not None:
                            val = gallery.get(f"{W}val", "")
                            if "Table of Contents" in val:
                                return True
            ancestor = ancestor.getparent()

        # 3. Kiểm tra w:instrText chứa "TOC" bên trong đoạn
        for instr_text in p_elem.iter(f"{W}instrText"):
            if instr_text.text and "TOC" in instr_text.text.upper():
                return True

        # 4. Kiểm tra w:fldSimple con bên trong đoạn
        for fld in p_elem.iter(f"{W}fldSimple"):
            instr = fld.get(f"{W}instr", "")
            if "TOC" in instr.upper():
                return True

        # 5. Kiểm tra phần tử cha trực tiếp là w:fldSimple
        parent = p_elem.getparent()
        if parent is not None and parent.tag == f"{W}fldSimple":
            instr = parent.get(f"{W}instr", "")
            if "TOC" in instr.upper():
                return True

        return False

    def _extract_paragraph_text(self, p_elem: etree._Element) -> str:
        """
        Trích xuất toàn bộ text thuần túy từ các thẻ w:t bên trong đoạn.

        Ghép nối text từ tất cả w:t (kể cả bên trong w:hyperlink, w:ins, ...)
        theo đúng thứ tự xuất hiện trong XML.
        """
        W = self._W
        fragments: List[str] = []
        for t_elem in p_elem.iter(f"{W}t"):
            if t_elem.text:
                fragments.append(t_elem.text)
        return "".join(fragments)


    def _get_content_paragraphs(
        self, body: etree._Element
    ) -> List[Tuple[etree._Element, str]]:
        """
        Thu thập tất cả đoạn văn có nội dung (không rỗng hoặc có chứa hình ảnh, không thuộc TOC).
        """
        W = self._W
        results: List[Tuple[etree._Element, str]] = []

        for p_elem in body.iter(f"{W}p"):
            if self._is_toc_paragraph(p_elem):
                continue

            text = self._extract_paragraph_text(p_elem)

            # Kiểm tra xem có chứa hình ảnh/media không
            has_media = False
            for child in p_elem.iter():
                if "drawing" in child.tag or "shape" in child.tag or "imagedata" in child.tag:
                    has_media = True
                    break

            # Bỏ qua đoạn rỗng nếu không có cả text lẫn media
            if not text.strip() and not has_media:
                continue

            results.append((p_elem, text))

        return results

    def _parse_p_pr(self, p_elem: etree._Element) -> Dict[str, str]:
        """
        Phân tích w:pPr để lấy các thuộc tính căn lề và thụt lề từ Word XML.
        Trả về dict các style CSS inline tương ứng.
        """
        W = self._W
        styles: Dict[str, str] = {}
        
        p_pr = p_elem.find(f"{W}pPr")
        if p_pr is not None:
            # 1. Căn lề (w:jc)
            jc = p_pr.find(f"{W}jc")
            if jc is not None:
                val = jc.get(f"{W}val", "")
                if val == "center":
                    styles["text-align"] = "center"
                elif val == "right":
                    styles["text-align"] = "right"
                elif val == "both":
                    styles["text-align"] = "justify"
                elif val == "left":
                    styles["text-align"] = "left"
            
            # 2. Thụt lề (w:ind)
            ind = p_pr.find(f"{W}ind")
            if ind is not None:
                # Lùi dòng trái (w:left)
                left = ind.get(f"{W}left")
                if left:
                    try:
                        # 1 twip = 1/20 pt. 1 pt = 1.33 px. twip -> px ~ chia cho 15
                        px = int(left) / 15
                        styles["margin-left"] = f"{px:.1f}px"
                    except ValueError:
                        pass
                
                # Thụt dòng đầu tiên (w:firstLine)
                first_line = ind.get(f"{W}firstLine")
                if first_line:
                    try:
                        px = int(first_line) / 15
                        styles["text-indent"] = f"{px:.1f}px"
                    except ValueError:
                        pass
                        
        return styles

    def _load_image_relationships(self, docx_path: str) -> Dict[str, str]:
        """
        Đọc và ánh xạ các relationship ID (rId) sang tên file ảnh thực tế.
        """
        import zipfile
        rels: Dict[str, str] = {}
        try:
            with zipfile.ZipFile(docx_path) as z:
                if "word/_rels/document.xml.rels" in z.namelist():
                    rels_data = z.read("word/_rels/document.xml.rels")
                    root = etree.fromstring(rels_data)
                    R_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
                    for rel in root.findall(f"{{{R_NS}}}Relationship"):
                        r_id = rel.get("Id")
                        target = rel.get("Target")
                        rel_type = rel.get("Type", "")
                        if "image" in rel_type.lower() and r_id and target:
                            filename = Path(target).name
                            rels[r_id] = filename
        except Exception as e:
            logger.warning("Không thể đọc quan hệ hình ảnh: %s", e)
        return rels

    def _paragraph_to_html(self, p_elem: etree._Element, image_rels: Dict[str, str], doc_filename: str) -> str:
        """
        Chuyển cấu trúc XML của đoạn văn thành chuỗi HTML,
        bảo toàn formatting bold, italic, underline, căn lề, thụt lề và ảnh inline.
        """
        W = self._W
        html_parts: List[str] = []
        
        # Lấy CSS căn dòng, thụt lề của Word
        styles_dict = self._parse_p_pr(p_elem)
        styles_str = "; ".join(f"{k}: {v}" for k, v in styles_dict.items())
        
        for child in p_elem:
            if child.tag == f"{W}r":
                html_parts.append(self._run_to_html(child, image_rels, doc_filename))
            elif child.tag == f"{W}hyperlink":
                link_text = []
                for sub_child in child:
                    if sub_child.tag == f"{W}r":
                        link_text.append(self._run_to_html(sub_child, image_rels, doc_filename))
                html_parts.append("".join(link_text))
            elif child.tag == f"{W}sdt":
                sdt_content = child.find(f"{W}sdtContent")
                if sdt_content is not None:
                    for sub in sdt_content:
                        if sub.tag == f"{W}r":
                            html_parts.append(self._run_to_html(sub, image_rels, doc_filename))
                            
        inner_html = "".join(html_parts)
        if styles_str:
            return f'<p style="{styles_str}">{inner_html}</p>'
        else:
            return f'<p>{inner_html}</p>'

    def _run_to_html(self, r_elem: etree._Element, image_rels: Dict[str, str], doc_filename: str) -> str:
        """
        Chuyển đổi một thẻ w:r sang HTML, bảo toàn format bold, italic, u và ảnh.
        """
        W = self._W
        A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
        R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        V_NS = "urn:schemas-microsoft-com:vml"
        
        r_pr = r_elem.find(f"{W}rPr")
        is_bold = False
        is_italic = False
        is_underline = False
        
        if r_pr is not None:
            if r_pr.find(f"{W}b") is not None:
                is_bold = True
            if r_pr.find(f"{W}i") is not None:
                is_italic = True
            if r_pr.find(f"{W}u") is not None:
                is_underline = True
                
        run_parts: List[str] = []
        
        for child in r_elem:
            if child.tag == f"{W}t":
                if child.text:
                    run_parts.append(child.text)
            elif child.tag == f"{W}drawing":
                for blip in child.iter(f"{{{A_NS}}}blip"):
                    r_embed = blip.get(f"{{{R_NS}}}embed")
                    if r_embed and r_embed in image_rels:
                        img_name = image_rels[r_embed]
                        src = f"/api/media/{doc_filename}/{img_name}"
                        run_parts.append(f'<img src="{src}" class="doc-img" alt="{img_name}" />')
            elif child.tag == f"{{urn:schemas-microsoft-com:vml}}shape":
                imagedata = child.find(f"{{{V_NS}}}imagedata")
                if imagedata is not None:
                    r_id = imagedata.get(f"{{{R_NS}}}id")
                    if r_id and r_id in image_rels:
                        img_name = image_rels[r_id]
                        src = f"/api/media/{doc_filename}/{img_name}"
                        run_parts.append(f'<img src="{src}" class="doc-img" alt="{img_name}" />')
                        
        content = "".join(run_parts)
        if not content:
            return ""
            
        if is_bold:
            content = f"<strong>{content}</strong>"
        if is_italic:
            content = f"<em>{content}</em>"
        if is_underline:
            content = f"<u>{content}</u>"
            
        return content

    def _replace_paragraph_text(
        self, p_elem: etree._Element, new_text: str
    ) -> None:
        """
        Thay thế toàn bộ text trong một đoạn bằng nội dung mới,
        nhưng giữ lại toàn bộ hình ảnh (w:drawing, v:shape) và bookmark.
        """
        W = self._W

        first_r_pr = None
        for r_elem in p_elem.iter(f"{W}r"):
            r_pr = r_elem.find(f"{W}rPr")
            if r_pr is not None:
                first_r_pr = copy.deepcopy(r_pr)
                break

        keep_tags = frozenset({
            f"{W}pPr",
            f"{W}bookmarkStart",
            f"{W}bookmarkEnd",
        })

        to_remove = []
        for child in p_elem:
            if child.tag in keep_tags:
                continue
                
            if child.tag == f"{W}r":
                has_media = False
                for sub in child.iter():
                    if "drawing" in sub.tag or "shape" in sub.tag or "imagedata" in sub.tag:
                        has_media = True
                        break
                
                if has_media:
                    for t_elem in list(child.findall(f"{W}t")):
                        child.remove(t_elem)
                    continue
                    
            to_remove.append(child)

        for elem in to_remove:
            p_elem.remove(elem)

        new_r = etree.SubElement(p_elem, f"{W}r")
        if first_r_pr is not None:
            new_r.append(first_r_pr)

        new_t = etree.SubElement(new_r, f"{W}t")
        new_t.text = new_text

        if new_text and (new_text[0] == " " or new_text[-1] == " "):
            new_t.set(self._XML_SPACE, "preserve")

    # ================================================================
    #  PUBLIC API
    # ================================================================

    def extract_paragraphs_with_ids(self, file_path: str) -> Dict[str, Dict[str, str]]:
        """
        Trích xuất các đoạn văn kèm ID tuần tự từ file .docx.

        Mở file .docx, truy cập word/document.xml, duyệt toàn bộ thẻ <w:p>
        và trả về dictionary chứa text thuần và HTML (có ảnh).

        Args:
            file_path: Đường dẫn đến file .docx cần xử lý.

        Returns:
            Dict dạng {"p_1": {"text": "...", "html": "..."}, ...}
        """
        file_path_str = str(file_path)
        path = Path(file_path_str)

        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path_str}")
        if path.suffix.lower() != ".docx":
            raise ValueError(
                f"File phải có định dạng .docx, nhận được: '{path.suffix}'"
            )

        try:
            doc = Document(file_path_str)
            body = doc.element.body
            paragraphs = self._get_content_paragraphs(body)
            
            # Đọc quan hệ hình ảnh
            image_rels = self._load_image_relationships(file_path_str)
            doc_filename = path.name

            result: Dict[str, Dict[str, str]] = {}
            for idx, (p_elem, text) in enumerate(paragraphs, start=1):
                html = self._paragraph_to_html(p_elem, image_rels, doc_filename)
                result[f"p_{idx}"] = {
                    "text": text,
                    "html": html or text  # Fallback nếu html trống
                }

            logger.info(
                "Đã trích xuất %d đoạn văn từ '%s'", len(result), file_path_str
            )
            return result

        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error(
                "Lỗi khi trích xuất đoạn văn từ '%s': %s", file_path_str, e
            )
            raise RuntimeError(
                f"Không thể trích xuất đoạn văn từ '{file_path_str}': {e}"
            ) from e

    def merge_edited_text(
        self,
        original_file_path: str,
        edited_json: Dict[str, str],
        output_file_path: str,
    ) -> None:
        """
        Gộp nội dung đã chỉnh sửa bởi AI vào file .docx gốc.
        """
        original_path_str = str(original_file_path)
        output_path_str = str(output_file_path)
        path = Path(original_path_str)

        if not path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file gốc: {original_path_str}"
            )
        if path.suffix.lower() != ".docx":
            raise ValueError(
                f"File phải có định dạng .docx, nhận được: '{path.suffix}'"
            )

        if not edited_json:
            logger.warning(
                "edited_json rỗng — sao chép nguyên file gốc sang '%s'.",
                output_path_str,
            )
            Path(output_path_str).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original_path_str, output_path_str)
            return

        try:
            doc = Document(original_path_str)
            body = doc.element.body
            paragraphs = self._get_content_paragraphs(body)

            p_index: Dict[str, etree._Element] = {}
            for idx, (p_elem, _) in enumerate(paragraphs, start=1):
                p_index[f"p_{idx}"] = p_elem

            unknown_ids = set(edited_json.keys()) - set(p_index.keys())
            if unknown_ids:
                logger.warning(
                    "Bỏ qua các ID không hợp lệ: %s (ID hợp lệ: p_1..p_%d)",
                    sorted(unknown_ids),
                    len(p_index),
                )

            applied_count = 0
            for p_id, new_text in edited_json.items():
                if p_id not in p_index:
                    continue

                self._replace_paragraph_text(p_index[p_id], new_text)
                applied_count += 1

            Path(output_path_str).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path_str)

            logger.info(
                "Đã gộp %d/%d chỉnh sửa → '%s'",
                applied_count,
                len(edited_json),
                output_path_str,
            )

        except (FileNotFoundError, ValueError):
            raise
        except Exception as e:
            logger.error("Lỗi khi gộp chỉnh sửa: %s", e)
            out = Path(output_path_str)
            if out.exists():
                try:
                    out.unlink()
                    logger.info("Đã xóa file đầu ra lỗi: '%s'", output_path_str)
                except OSError:
                    pass
            raise RuntimeError(f"Không thể gộp chỉnh sửa: {e}") from e
