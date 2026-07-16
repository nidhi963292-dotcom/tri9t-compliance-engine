# app/versioning.py
import difflib

def check_staleness(original_node, v2_nodes_dict: dict) -> dict:
    """
    Compares an original pinned node against a dictionary of nodes from a new version.
    Matches nodes by their heading structure (heading_number_heading_title).
    """
    # 1. Build the lookup key format matching main.py
    h_num = original_node.heading_number if original_node.heading_number else ""
    h_title = original_node.heading_title if original_node.heading_title else ""
    lookup_key = f"{h_num}_{h_title}"
    
    # 2. Check if the section still exists in the new version
    if lookup_key not in v2_nodes_dict:
        return {
            "is_stale": True,
            "reason": "Section heading was completely removed or renamed in this version.",
            "diff_ratio": 0.0
        }
        
    new_node = v2_nodes_dict[lookup_key]
    
    # 3. Clean and prepare text strings for comparison
    orig_text = original_node.body_text.strip() if original_node.body_text else ""
    new_text = new_node.body_text.strip() if new_node.body_text else ""
    
    # Handle table data comparison if text is empty but tables exist
    if not orig_text and not new_text:
        orig_text = str(original_node.table_data or "")
        new_text = str(new_node.table_data or "")

    # 4. Calculate structural text similarity ratio (0.0 to 1.0)
    matcher = difflib.SequenceMatcher(None, orig_text, new_text)
    diff_ratio = matcher.ratio()
    
    # 5. Flag as stale if the text has changed at all (ratio less than 1.0)
    if diff_ratio < 1.0:
        change_percentage = round((1.0 - diff_ratio) * 100, 1)
        return {
            "is_stale": True,
            "reason": f"Text content modified (roughly {change_percentage}% variation detected).",
            "diff_ratio": diff_ratio
        }
        
    return {
        "is_stale": False,
        "reason": "Content matches perfectly.",
        "diff_ratio": 1.0
    }