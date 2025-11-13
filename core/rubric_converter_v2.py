"""
Improved Rubric Converter: Handles TikZ graphs and preserves question parts.

Key improvements:
1. Extracts and compiles TikZ graphs to SVG
2. Preserves all question parts (a, b, c) with their text
3. Keeps solution boxes intact
"""

import subprocess
import re
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Tuple, List
import hashlib


def extract_tikz_figures(latex_content: str) -> Tuple[str, Dict[str, str]]:
    """
    Extract TikZ figures from LaTeX and replace with placeholders.
    
    Returns:
        (modified_latex, {placeholder_id: tikz_code})
    """
    figures = {}
    figure_pattern = r'\\begin\{figure\}.*?\\end\{figure\}'
    
    def replace_figure(match):
        figure_content = match.group(0)
        
        # Only process if it contains tikzpicture
        if 'tikzpicture' in figure_content:
            # Generate unique ID
            fig_id = hashlib.md5(figure_content.encode()).hexdigest()[:8]
            figures[fig_id] = figure_content
            return f'TIKZ_PLACEHOLDER_{fig_id}'
        return figure_content
    
    modified_latex = re.sub(figure_pattern, replace_figure, latex_content, flags=re.DOTALL)
    return modified_latex, figures


def compile_tikz_to_svg(tikz_code: str, output_path: str, group_id: str) -> bool:
    """
    Compile a single TikZ figure to SVG.
    
    Uses standalone class + pdf2svg pipeline.
    """
    # Create complete LaTeX document
    latex_doc = f"""\\documentclass[tikz,border=10pt]{{standalone}}
\\usepackage{{tkz-graph}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}

\\newcommand{{\\el}}[3]{{\\Edge[label=$#1$](#2)(#3)}}
\\newcommand{{\\vl}}[3]{{\\Vertex[x = #1, y = #2]{{#3}}}}

\\begin{{document}}
{tikz_code}
\\end{{document}}
"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Write LaTeX
        tex_file = tmpdir / f"{group_id}_graph.tex"
        with open(tex_file, 'w') as f:
            f.write(latex_doc)
        
        try:
            # Compile to PDF
            subprocess.run([
                'pdflatex',
                '-interaction=nonstopmode',
                '-output-directory', str(tmpdir),
                str(tex_file)
            ], capture_output=True, check=True, timeout=30)
            
            pdf_file = tmpdir / f"{group_id}_graph.pdf"
            
            # Convert PDF to SVG
            subprocess.run([
                'pdf2svg',
                str(pdf_file),
                output_path
            ], check=True, timeout=10)
            
            return True
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"  ⚠ Failed to compile TikZ: {e}")
            return False


def preprocess_latex_with_parts(latex_content: str) -> str:
    """
    Preprocess LaTeX while preserving question parts structure.
    
    Converts:
    - \\question[pts] → section
    - \\part[pts] → subsection WITH the question text that follows
    - \\begin{parts} → custom marker
    - solutionbox → styled div
    """
    # Replace \begin{questions} and \end{questions}
    latex_content = latex_content.replace(r'\begin{questions}', '')
    latex_content = latex_content.replace(r'\end{questions}', '')
    
    # Mark parts environment
    latex_content = latex_content.replace(r'\begin{parts}', r'\par\textbf{PARTS\_BEGIN}\par')
    latex_content = latex_content.replace(r'\end{parts}', r'\par\textbf{PARTS\_END}\par')
    
    # Convert \question[points] to section
    latex_content = re.sub(
        r'\\question\[(\d+)\]',
        r'\\section*{Question (\\textbf{\1 points})}',
        latex_content
    )
    
    # Convert \part[points] - but keep it simple for Pandoc
    latex_content = re.sub(
        r'\\part\[(\d+)\]\s*',
        r'\\subsection*{Part (\\textbf{\1 points})} ',
        latex_content
    )
    
    # Convert solutionbox to custom environment
    # Pattern: \begin{solutionbox}{\stretch{1}}  →  \begin{quote}\textbf{SOLUTION:}
    latex_content = re.sub(
        r'\\begin\{solutionbox\}\{[^}]*\}',
        r'\\begin{quote}\\textbf{SOLUTION:}',
        latex_content
    )
    latex_content = latex_content.replace(r'\end{solutionbox}', r'\\end{quote}')
    
    return latex_content


def extract_latex_section(tex_file: str, line_range: Tuple[int, int]) -> str:
    """Extract specific line range from LaTeX file."""
    with open(tex_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    start, end = line_range
    return ''.join(lines[start-1:end])


def latex_to_html_with_figures(
    latex_content: str,
    group_id: str,
    quiz_id: int,
    tikz_figures: Dict[str, str]
) -> str:
    """
    Convert LaTeX to HTML using Pandoc, then reinsert compiled TikZ as images.
    """
    # Preprocess
    latex_content = preprocess_latex_with_parts(latex_content)
    
    # Create wrapper document
    full_latex = f"""\\documentclass{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}
\\usepackage{{amsthm}}
\\usepackage{{booktabs}}
\\begin{{document}}
{latex_content}
\\end{{document}}
"""
    
    # Write to temp file
    temp_tex = Path(f"temp_{group_id}.tex")
    temp_html = Path(f"temp_{group_id}.html")
    
    try:
        with open(temp_tex, 'w', encoding='utf-8') as f:
            f.write(full_latex)
        
        # Run Pandoc
        result = subprocess.run([
            'pandoc',
            str(temp_tex),
            '-o', str(temp_html),
            '--standalone',
            '--mathjax',
            '--from=latex',
            '--to=html5',
            '--css=https://cdn.jsdelivr.net/npm/water.css@2/out/water.css'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"      Pandoc error:\n{result.stderr}")
            # Try to continue anyway
            if not Path(temp_html).exists():
                raise RuntimeError(f"Pandoc failed: {result.stderr}")
        
        # Read result
        with open(temp_html, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Compile TikZ figures and replace placeholders
        image_dir = Path(f"templates/quiz{quiz_id}/images")
        image_dir.mkdir(parents=True, exist_ok=True)
        
        for fig_id, tikz_code in tikz_figures.items():
            placeholder = f'TIKZ_PLACEHOLDER_{fig_id}'
            if placeholder in html:
                svg_path = image_dir / f"{group_id}_{fig_id}.svg"
                
                print(f"    - Compiling TikZ graph {fig_id}...")
                if compile_tikz_to_svg(tikz_code, str(svg_path), f"{group_id}_{fig_id}"):
                    # Replace placeholder with img tag
                    img_tag = f'<img src="images/{group_id}_{fig_id}.svg" alt="Graph" class="tikz-graph" />'
                    html = html.replace(placeholder, img_tag)
                else:
                    print(f"      ⚠ Failed to compile graph {fig_id}, leaving placeholder")
        
        return html
        
    finally:
        # Clean up temp files
        if temp_tex.exists():
            temp_tex.unlink()
        if temp_html.exists():
            temp_html.unlink()


def add_question_structure_and_placeholders(html: str, group: dict) -> str:
    """
    Parse HTML and add:
    - data-version attributes for each question
    - Answer placeholders for each part
    - Proper styling
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all sections (questions)
    sections = soup.find_all('h1', string=re.compile(r'Question'))
    
    question_version = 1
    part_letter = ['a', 'b', 'c', 'd', 'e']
    
    for section in sections:
        # Create wrapper for this question version
        wrapper = soup.new_tag('div', **{
            'class': 'question-version',
            'data-version': str(question_version),
            'data-group': group['id']
        })
        
        # Collect all content until next question section
        current = section
        elements_to_wrap = []
        
        while current:
            elements_to_wrap.append(current)
            current = current.next_sibling
            
            # Stop if we hit another question
            if current and current.name == 'h1' and current.find(string=re.compile(r'Question')):
                break
        
        # Move elements into wrapper
        for elem in elements_to_wrap:
            if elem.parent:
                elem.extract()
        
        for elem in elements_to_wrap:
            wrapper.append(elem)
        
        # Insert wrapper
        if elements_to_wrap:
            section.parent.insert(0, wrapper)
        
        # Add answer placeholders for each part
        part_idx = 0
        subsections = wrapper.find_all('h2', string=re.compile(r'Part'))
        
        for subsection in subsections:
            if part_idx < len(group['tags']):
                tag = group['tags'][part_idx]
                
                # Create answer section
                answer_div = soup.new_tag('div', **{
                    'class': 'student-answer-section',
                    'data-tag': tag
                })
                
                answer_heading = soup.new_tag('h4')
                answer_heading.string = f"Student Answer ({tag}):"
                answer_div.append(answer_heading)
                
                answer_content = soup.new_tag('div', **{'class': 'answer-placeholder'})
                answer_content.string = f"{{{{ANSWER_{tag.replace('.', '_')}}}}}"
                answer_div.append(answer_content)
                
                # Insert after the solution box (if present)
                # Find the quote (solution box) after this subsection
                next_quote = subsection.find_next('blockquote')
                if next_quote:
                    next_quote.insert_after(answer_div)
                else:
                    subsection.insert_after(answer_div)
                
                part_idx += 1
        
        question_version += 1
    
    # Add custom CSS
    style = soup.new_tag('style')
    style.string = """
        .question-version {
            margin: 3em 0;
            padding: 2em;
            border: 3px solid #2c3e50;
            border-radius: 10px;
            background-color: #fff;
        }
        .question-version[style*="display: none"] {
            display: none !important;
        }
        .tikz-graph {
            display: block;
            margin: 2em auto;
            max-width: 100%;
            height: auto;
        }
        blockquote {
            background-color: #e8f5e9;
            border-left: 5px solid #4caf50;
            padding: 1.5em;
            margin: 1.5em 0;
        }
        blockquote strong {
            color: #2e7d32;
        }
        .student-answer-section {
            margin: 2em 0;
            padding: 1.5em;
            background-color: #fff3e0;
            border-left: 5px solid #ff9800;
            border-radius: 5px;
        }
        .student-answer-section h4 {
            margin-top: 0;
            color: #e65100;
        }
        .answer-placeholder {
            padding: 1em;
            background-color: white;
            border: 2px dashed #ff9800;
            min-height: 60px;
            font-family: monospace;
            color: #666;
        }
        h1 {
            color: #1565c0;
            border-bottom: 3px solid #1565c0;
            padding-bottom: 0.5em;
        }
        h2 {
            color: #0277bd;
            margin-top: 1.5em;
        }
    """
    
    if soup.head:
        soup.head.append(style)
    
    return str(soup)


def convert_rubric_to_templates(config: dict) -> Dict[str, str]:
    """
    Main function: Convert LaTeX rubric to HTML templates.
    
    Handles:
    - TikZ graphs → SVG images
    - Question parts preservation
    - Answer placeholders
    """
    rubric_path = f"rubrics/{config['rubric_file']}"
    
    print(f"\n📝 Converting rubric: {rubric_path}")
    
    templates = {}
    for group in config['question_groups']:
        print(f"\n  Processing {group['name']} ({group['id']})...")
        print(f"    - Extracting lines {group['latex_line_range'][0]}-{group['latex_line_range'][1]}")
        
        # Extract LaTeX for this question group
        latex_content = extract_latex_section(
            rubric_path, 
            group['latex_line_range']
        )
        
        # Extract TikZ figures
        print(f"    - Extracting TikZ figures...")
        latex_content, tikz_figures = extract_tikz_figures(latex_content)
        print(f"      Found {len(tikz_figures)} TikZ figures")
        
        # Convert to HTML
        print(f"    - Converting to HTML with Pandoc...")
        html = latex_to_html_with_figures(
            latex_content,
            group['id'],
            config['quiz_id'],
            tikz_figures
        )
        
        # Add structure and placeholders
        print(f"    - Adding question structure and answer placeholders...")
        html = add_question_structure_and_placeholders(html, group)
        
        templates[group['id']] = html
        print(f"    ✓ Template generated for {group['id']}")
    
    return templates


def save_templates(templates: Dict[str, str], quiz_id: int) -> None:
    """Save HTML templates to files."""
    output_dir = Path(f"templates/quiz{quiz_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for group_id, html in templates.items():
        output_file = output_dir / f"{group_id}_template.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  💾 Saved: {output_file}")

