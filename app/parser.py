# app/parser.py
import re
import hashlib
import json
import pdfplumber
from typing import List, Dict, Any, Optional

# Regular expression matching standard document hierarchical numbers
NUMBER_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.*)$')

class ParsedNode:
    def __init__(self, id: str, heading_number: str, heading_title: str, level: int, page: int, top: float):
        self.id = id
        self.heading_number = heading_number
        self.heading_title = heading_title
        self.level = level
        self.page = page
        self.top = top
        self.parent_id: Optional[str] = None
        self.body_text: str = ""
        self.table_data: Optional[List[List[Any]]] = None

    def finalize_hash(self):
        """Generates a contextual content hash covering text and tabular values."""
        hasher = hashlib.sha256()
        hasher.update(self.body_text.encode('utf-8'))
        if self.table_data:
            hasher.update(json.dumps(self.table_data).encode('utf-8'))
        return hasher.hexdigest()

def parse_pdf(pdf_path: str, version_tag: str) -> List[ParsedNode]:
    all_nodes: List[ParsedNode] = []
    current_node: Optional[ParsedNode] = None
    
    # Pre-calculated benchmark font sizes to decouple headings from text items
    # Typically, H1=16pt, H2=13pt, H3=11pt, H4=10pt Bold (Body is 10pt Regular)
    BODY_FONT_SIZE = 10.0

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract distinct tabular configurations on this page layout
            tables = page.find_tables()
            table_bboxes = [t.bbox for t in tables]
            extracted_tables = [t.extract() for t in tables]
            
            # Extract individual strings preserving exact layout coordinates
            words = page.extract_words(extra_attrs=["fontname", "size"])
            
            # Reconstruct lines based on vertical positioning alignments
            lines_dict: Dict[float, List[Dict[str, Any]]] = {}
            for w in words:
                # Discard items sitting squarely inside parsed geometric table coordinate spaces
                in_table = False
                for bbox in table_bboxes:
                    if bbox[0] <= w["x0"] <= bbox[2] and bbox[1] <= w["top"] <= bbox[3]:
                        in_table = True
                        break
                if in_table:
                    continue
                
                top_rounded = round(w["top"], 1)
                lines_dict.setdefault(top_rounded, []).append(w)
            
            # Sort individual lines chronologically top-down
            sorted_tops = sorted(lines_dict.keys())
            
            for top in sorted_tops:
                line_words = sorted(lines_dict[top], key=lambda x: x["x0"])
                line_text = " ".join([w["text"] for w in line_words]).strip()
                if not line_text:
                    continue
                
                # Check formatting features on the initial characters
                sample_word = line_words[0]
                is_bold = "Bold" in sample_word["fontname"]
                size = sample_word["size"]
                
                match = NUMBER_RE.match(line_text)
                
                # HEURISTIC: Must match dotted formatting notation, have heading font-scale or weight traits
                if match and (size > BODY_FONT_SIZE or is_bold):
                    num_part = match.group(1)
                    title_part = match.group(2)
                    
                    # Deduce hierarchy depth strictly via dot configurations
                    level = len(num_part.split('.'))
                    
                    # Address structural loops by assigning uniqueness using version tags
                    node_id = f"{version_tag}_{num_part}_{hashlib.md5(title_part.encode()).hexdigest()[:6]}"
                    
                    new_node = ParsedNode(node_id, num_part, title_part, level, page_num, top)
                    
                    # Tree assembly matching logic supporting arbitrary hierarchy drops/skips
                    if all_nodes:
                        potential_parent = None
                        for p in reversed(all_nodes):
                            if p.level < new_node.level:
                                potential_parent = p
                                break
                        if potential_parent:
                            new_node.parent_id = potential_parent.id
                            
                    all_nodes.append(new_node)
                    current_node = new_node
                else:
                    # Collect regular lines into the currently active heading block
                    if current_node:
                        current_node.body_text += (" " + line_text if current_node.body_text else line_text)
            
            # Layout Mapping Check: Connect data tables to their nearest preceding headers
            for t_idx, bbox in enumerate(table_bboxes):
                tbl_top = bbox[1]
                nearest_node = None
                max_top = -1.0
                
                for node in all_nodes:
                    if node.page == page_num and node.top < tbl_top:
                        if node.top > max_top:
                            max_top = node.top
                            nearest_node = node
                            
                if nearest_node:
                    nearest_node.table_data = extracted_tables[t_idx]

    # Clean text spacings and compute data signatures
    for node in all_nodes:
        node.body_text = node.body_text.strip()
    return all_nodes