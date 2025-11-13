"""
Final Rubric Converter: Simplified, robust approach.

Strategy:
1. Pre-compile ALL TikZ graphs to standalone images using LaTeX
2. Replace TikZ code with simple image markers
3. Use Pandoc to convert cleaned LaTeX to HTML
4. Post-process HTML to add structure and placeholders
"""

import subprocess
import re
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Tuple, List
import hashlib


def extract_and_compile_tikz_graphs(latex_content: str, group_id: str, quiz_id: int) -> Tuple[str, Dict[str, Path]]:
    """
    Extract TikZ figures, compile each to SVG, return modified LaTeX with image paths.
    
    Returns:
        (latex_with_image_markers, {figure_id: svg_file_path})
    """
    # Create output directory for images
    img_dir = Path(f"templates/quiz{quiz_id}/images")
    img_dir.mkdir(parents=True, exist_ok=True)
    
    # Pattern to find figure environments with tikzpicture
    figure_pattern = r'\\begin\{figure\}\[H\](.*?)\\end\{figure\}'
    
    compiled_images = {}
    figure_counter = 1
    
    def replace_and_compile(match):
        nonlocal figure_counter
        full_figure = match.group(0)
        figure_content = match.group(1)
        
        # Check if this figure contains TikZ
        if 'tikzpicture' not in figure_content:
            return full_figure
        
        # Generate figure ID
        fig_id = f"fig_{figure_counter:02d}"
        figure_counter += 1
        
        # Extract the tikzpicture environment
        tikz_match = re.search(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', figure_content, re.DOTALL)
        if not tikz_match:
            return full_figure
        
        tikz_code = tikz_match.group(0)
        
        # Compile to SVG
        svg_path = img_dir / f"{group_id}_{fig_id}.svg"
        
        print(f"      Compiling graph {fig_id}...")
        if compile_tikz_to_svg(tikz_code, svg_path, f"{group_id}_{fig_id}"):
            compiled_images[fig_id] = svg_path
            # Replace with simple image reference marker
            return f"\\par\\noindent IMAGE_MARKER_{fig_id} \\par"
        else:
            print(f"        ⚠ Failed, skipping")
            return full_figure
    
    # Replace all figures
    modified_latex = re.sub(figure_pattern, replace_and_compile, latex_content, flags=re.DOTALL)
    
    return modified_latex, compiled_images


def compile_tikz_to_svg(tikz_code: str, output_svg: Path, temp_name: str) -> bool:
    """
    Compile TikZ code to SVG using standalone class + pdf2svg.
    """
    # Create complete standalone document
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
        tex_file = tmpdir / f"{temp_name}.tex"
        with open(tex_file, 'w') as f:
            f.write(latex_doc)
        
        try:
            # Compile to PDF
            result = subprocess.run([
                'pdflatex',
                '-interaction=nonstopmode',
                '-output-directory', str(tmpdir),
                str(tex_file)
            ], capture_output=True, timeout=15)
            
            if result.returncode != 0:
                return False
            
            pdf_file = tmpdir / f"{temp_name}.pdf"
            if not pdf_file.exists():
                return False
            
            # Convert PDF to SVG
            result = subprocess.run([
                'pdf2svg',
                str(pdf_file),
                str(output_svg)
            ], capture_output=True, timeout=10)
            
            return result.returncode == 0 and output_svg.exists()
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False


def preprocess_exam_latex(latex_content: str) -> str:
    """
    Convert exam class environments to standard LaTeX.
    """
    # Remove questions/parts environment markers
    latex_content = latex_content.replace(r'\begin{questions}', '')
    latex_content = latex_content.replace(r'\end{questions}', '')
    latex_content = latex_content.replace(r'\begin{parts}', '')
    latex_content = latex_content.replace(r'\end{parts}', '')
    
    # Convert \question[points] to section
    latex_content = re.sub(
        r'\\question\[(\d+)\]',
        r'\\section*{Question (\1 points)}',
        latex_content
    )
    
    # Convert \part[points] to subsection
    latex_content = re.sub(
        r'\\part\[(\d+)\]\s*',
        r'\\subsection*{Part (\1 points)}',
        latex_content
    )
    
    # Convert solutionbox to quote
    latex_content = re.sub(
        r'\\begin\{solutionbox\}\{[^}]*\}',
        r'\\begin{quote}\\textbf{Solution:}',
        latex_content
    )
    latex_content = latex_content.replace(r'\end{solutionbox}', r'\\end{quote}')
    
    return latex_content


def latex_to_html_pandoc(latex_content: str, group_id: str) -> str:
    """
    Convert preprocessed LaTeX to HTML using Pandoc.
    """
    # Create full document
    full_latex = f"""\\documentclass{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}
\\usepackage{{amsthm}}
\\begin{{document}}
{latex_content}
\\end{{document}}
"""
    
    # Write temp file
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
            print(f"      ⚠ Pandoc warning:\n{result.stderr}")
        
        # Read result
        with open(temp_html, 'r', encoding='utf-8') as f:
            return f.read()
        
    finally:
        # Clean up
        if temp_tex.exists():
            temp_tex.unlink()
        if temp_html.exists():
            temp_html.unlink()


def add_structure_and_placeholders(html: str, group: dict, compiled_images: Dict[str, Path]) -> str:
    """
    Post-process HTML to add:
    1. Question version wrappers with data-version attributes
    2. Replace IMAGE_MARKER_XX with actual <img> tags
    3. Add answer placeholders after each part
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Replace image markers with actual img tags
    for fig_id, img_path in compiled_images.items():
        marker = f"IMAGE_MARKER_{fig_id}"
        # Find the text node with this marker
        for text in soup.find_all(string=re.compile(marker)):
            img_tag = soup.new_tag('img', src=f"images/{img_path.name}", **{
                'class': 'tikz-graph',
                'alt': f'Graph {fig_id}'
            })
            # Replace the text node with img tag
            text.replace_with(img_tag)
    
    # Find all question sections (h1 tags with "Question")
    sections = soup.find_all('h1', string=re.compile(r'Question.*points'))
    
    version_num = 1
    for section in sections:
        # Create wrapper div for this question version
        wrapper = soup.new_tag('div', **{
            'class': 'question-version',
            'data-version': str(version_num),
            'data-group': group['id']
        })
        
        # Collect all elements belonging to this question
        # (until we hit the next h1 question or end of document)
        elements_to_wrap = []
        current = section
        
        while current:
            elements_to_wrap.append(current)
            current = current.next_sibling
            
            # Stop at next question
            if current and current.name == 'h1' and 'Question' in str(current.string):
                break
        
        # Move elements into wrapper
        for elem in elements_to_wrap:
            if elem.parent:
                elem.extract()
        
        for elem in elements_to_wrap:
            wrapper.append(elem)
        
        # Insert wrapper back
        if section.parent:
            section.parent.insert(0, wrapper)
        
        # Now find all parts (h2 tags with "Part") within this wrapper
        parts = wrapper.find_all('h2', string=re.compile(r'Part.*points'))
        
        for part_idx, part in enumerate(parts):
            if part_idx < len(group['tags']):
                tag = group['tags'][part_idx]
                
                # Find the solution (quote) that follows this part
                solution_quote = part.find_next('blockquote')
                
                # Create student answer section
                answer_section = soup.new_tag('div', **{
                    'class': 'student-answer-section',
                    'data-tag': tag
                })
                
                answer_heading = soup.new_tag('h3')
                answer_heading.string = f"Student Answer for {tag}:"
                answer_section.append(answer_heading)
                
                answer_placeholder = soup.new_tag('div', **{'class': 'answer-placeholder'})
                answer_placeholder.string = f"{{{{ANSWER_{tag.replace('.', '_')}}}}}"
                answer_section.append(answer_placeholder)
                
                # Insert after solution box
                if solution_quote:
                    solution_quote.insert_after(answer_section)
        
        version_num += 1
    
    # Add custom CSS
    style_tag = soup.new_tag('style')
    style_tag.string = """
        body {
            max-width: 900px;
            margin: 0 auto;
            padding: 2em;
        }
        .question-version {
            margin: 3em 0;
            padding: 2em;
            border: 3px solid #1565c0;
            border-radius: 10px;
            background-color: #fafafa;
            page-break-after: always;
        }
        .question-version[style*="display: none"] {
            display: none !important;
        }
        .tikz-graph {
            display: block;
            margin: 2em auto;
            max-width: 600px;
            height: auto;
            border: 1px solid #ddd;
            padding: 10px;
            background: white;
        }
        blockquote {
            background-color: #e8f5e9;
            border-left: 5px solid #4caf50;
            padding: 1.5em;
            margin: 1.5em 0;
            border-radius: 5px;
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
        .student-answer-section h3 {
            margin-top: 0;
            color: #e65100;
            font-size: 1.1em;
        }
        .answer-placeholder {
            padding: 1.5em;
            background-color: white;
            border: 2px dashed #ff9800;
            min-height: 80px;
            font-family: 'Courier New', monospace;
            color: #888;
            font-size: 0.9em;
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
        p {
            line-height: 1.6;
        }
    """
    
    if soup.head:
        soup.head.append(style_tag)
    
    return str(soup.prettify())


def extract_latex_section(tex_file: str, line_range: Tuple[int, int]) -> str:
    """Extract lines from LaTeX file."""
    with open(tex_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    start, end = line_range
    return ''.join(lines[start-1:end])


def convert_rubric_to_templates(config: dict) -> Dict[str, str]:
    """
    Main conversion function.
    """
    rubric_path = f"rubrics/{config['rubric_file']}"
    
    print(f"\n📝 Converting rubric: {rubric_path}")
    
    templates = {}
    for group in config['question_groups']:
        print(f"\n  Processing {group['name']} ({group['id']})...")
        print(f"    - Extracting lines {group['latex_line_range'][0]}-{group['latex_line_range'][1]}")
        
        # Extract LaTeX section
        latex_content = extract_latex_section(rubric_path, group['latex_line_range'])
        
        # Extract and compile TikZ graphs
        print(f"    - Extracting and compiling TikZ graphs...")
        latex_content, compiled_images = extract_and_compile_tikz_graphs(
            latex_content,
            group['id'],
            config['quiz_id']
        )
        print(f"      ✓ Compiled {len(compiled_images)} graphs")
        
        # Preprocess exam class syntax
        print(f"    - Preprocessing LaTeX...")
        latex_content = preprocess_exam_latex(latex_content)
        
        # Convert to HTML
        print(f"    - Converting to HTML with Pandoc...")
        html = latex_to_html_pandoc(latex_content, group['id'])
        
        # Add structure and placeholders
        print(f"    - Adding question structure and answer placeholders...")
        html = add_structure_and_placeholders(html, group, compiled_images)
        
        templates[group['id']] = html
        print(f"    ✓ Template complete for {group['id']}")
    
    return templates


def save_templates(templates: Dict[str, str], quiz_id: int) -> None:
    """Save templates to disk."""
    output_dir = Path(f"templates/quiz{quiz_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for group_id, html in templates.items():
        output_file = output_dir / f"{group_id}_template.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  💾 Saved: {output_file}")

