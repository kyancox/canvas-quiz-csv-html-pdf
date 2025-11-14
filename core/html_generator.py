"""
HTML Generator: Map student answers to HTML templates.

Takes HTML templates and student data, then:
1. Hides all question versions except the one the student received
2. Replaces answer placeholders with student's HTML
"""

from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict


def load_template(template_path: str) -> str:
    """Load HTML template from file."""
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def sanitize_filename(name: str) -> str:
    """
    Convert student name to safe filename.
    
    Examples:
        "Alice Smith" → "Alice_Smith"
        "O'Brien, John" → "OBrien_John"
    """
    # Remove special characters, replace spaces with underscores
    name = re.sub(r'[^\w\s-]', '', name)
    name = name.replace(' ', '_')
    return name


def hide_other_variants(html: str, variant_to_show: int) -> str:
    """
    Hide all question variants except the specified one.
    
    Args:
        html: Full HTML template with all variants
        variant_to_show: Variant number to display (1-12)
        
    Returns:
        Modified HTML with only student's variant
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all question-version divs
    variant_divs = soup.find_all('div', class_='question-version')
    print(f"      Found {len(variant_divs)} question variants in template")
    
    # Find the one to keep
    variant_to_keep = None
    for div in variant_divs:
        version = div.get('data-version', '')
        if version == str(variant_to_show):
            variant_to_keep = div
            print(f"      Showing variant {version}")
            break
    
    # Remove all variant divs
    for div in variant_divs:
        try:
            div.extract()  # Remove from tree but don't destroy
        except:
            pass
    
    # Re-add only the one we want
    if variant_to_keep and soup.body:
        soup.body.append(variant_to_keep)
    
    return str(soup)


def insert_student_answers(html: str, answers: Dict[str, str]) -> str:
    """
    Replace answer placeholders with student's HTML.
    
    Replaces: {{PART_A}}, {{PART_B}}, etc. with actual student answers
    
    Args:
        html: HTML template with placeholders
        answers: Dict mapping part letter → answer HTML
                 Example: {'a': '<p>6</p>', 'b': '<p>{s},{t}</p>'}
        
    Returns:
        HTML with answers inserted
    """
    for part_letter, answer_html in answers.items():
        # Convert to placeholder format: {{PART_A}}, {{PART_B}}, etc.
        placeholder = f"{{{{PART_{part_letter.upper()}}}}}"
        
        # Replace placeholder with actual answer
        # If answer is empty, insert a note
        if answer_html and answer_html.strip():
            html = html.replace(placeholder, answer_html)
        else:
            html = html.replace(placeholder, '<p><em>(No answer provided)</em></p>')
    
    return html


def generate_student_html(
    template_html: str,
    student_data: Dict,
    group_id: str
) -> str:
    """
    Generate complete HTML for one student and one question group.
    
    Args:
        template_html: Full HTML template (all variants)
        student_data: Student dict with variant and answers
        group_id: Question group ID (e.g., 'q1')
        
    Returns:
        Complete HTML ready for PDF rendering
    """
    # Get student's data for this question group
    group_data = student_data[group_id]
    variant = group_data['variant']
    answers = group_data['answers']
    
    # Hide other variants
    html = hide_other_variants(template_html, variant)
    
    # Insert student answers
    html = insert_student_answers(html, answers)
    
    # Add student info header
    soup = BeautifulSoup(html, 'html.parser')
    
    # Create student info header
    info_div = soup.new_tag('div', **{
        'class': 'student-info',
        'style': 'background: #e3f2fd; padding: 1em; margin-bottom: 2em; border-radius: 5px;'
    })
    
    info_heading = soup.new_tag('h2')
    info_heading['style'] = 'margin-top: 0;'
    info_heading.string = f"Student: {student_data['name']}"
    info_div.append(info_heading)
    
    info_p = soup.new_tag('p')
    info_p['style'] = 'margin: 0;'
    info_p.string = f"ID: {student_data.get('id', 'N/A')}"
    info_div.append(info_p)
    
    # Insert at top of body
    body = soup.find('body')
    if body:
        body.insert(0, info_div)
    
    return str(soup)


import re  # Need to import for sanitize_filename

