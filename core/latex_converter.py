"""
LaTeX Converter: Convert student LaTeX answers to MathJax format.

Students often type "LaTeX: <expression>" in Canvas.
We need to convert these to MathJax inline math: \\(<expression>\\)
"""

import re


def convert_latex_in_html(html: str) -> str:
    r"""
    Convert "LaTeX: <expr>" patterns to MathJax inline math.
    
    Transforms:
        "LaTeX: C_1,C_2,\ldots,C_n" → "\(C_1,C_2,\ldots,C_n\)"
    
    Args:
        html: HTML string containing potential LaTeX patterns
        
    Returns:
        HTML with LaTeX converted to MathJax format
    """
    # Find all "LaTeX: " occurrences and convert them one by one
    result = []
    last_end = 0
    
    for match in re.finditer(r'LaTeX:\s*', html):
        # Add text before this match
        result.append(html[last_end:match.start()])
        
        # Extract the LaTeX expression after "LaTeX: "
        start = match.end()
        text = html[start:]
        
        # Find where the LaTeX expression ends
        expr = ""
        i = 0
        depth = 0  # Track \left...\right nesting
        
        while i < len(text):
            # Check for \left or \right
            if text[i:i+5] == '\\left':
                expr += text[i:i+5]
                depth += 1
                i += 5
                continue
            elif text[i:i+6] == '\\right':
                expr += text[i:i+6]
                depth -= 1
                i += 6
                # Continue if still nested
                if depth > 0:
                    continue
                # If depth is 0, check next char
                if i < len(text) and text[i] in ' \n\t':
                    # LaTeX expression complete
                    break
                continue
            
            # Stop at HTML tags (if not nested)
            if depth == 0 and text[i] == '<':
                break
            
            # Stop at common word boundaries (if not nested)
            if depth == 0:
                # Check for space followed by common words
                next_word_match = re.match(r'\s+(with|to|from|of|as|which|where|and|the|is|in|that|for|if|on)\s', text[i:], re.IGNORECASE)
                if next_word_match:
                    break
            
            expr += text[i]
            i += 1
        
        # Clean and add converted expression
        expr = expr.strip().rstrip(',.;:')
        result.append(f'\\({expr}\\)')
        last_end = start + i
    
    # Add remaining text
    result.append(html[last_end:])
    
    return ''.join(result)


def convert_canvas_equation_images(html: str) -> str:
    """
    Convert Canvas equation images to MathJax.
    
    Canvas converts "LaTeX: expr" to:
    <img class="equation_image" data-equation-content="expr" .../>
    
    We extract the data-equation-content and wrap in \\(...\\)
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all Canvas equation images
    eq_images = soup.find_all('img', class_='equation_image')
    
    for img in eq_images:
        # Get the LaTeX content
        latex_content = img.get('data-equation-content', '')
        
        if latex_content:
            # Create MathJax span
            math_span = soup.new_tag('span', **{'class': 'math inline'})
            math_span.string = f'\\({latex_content}\\)'
            
            # Replace image with span
            img.replace_with(math_span)
    
    return str(soup)


def sanitize_student_answer(answer_html: str) -> str:
    """
    Clean up student HTML answer for PDF rendering.
    
    - Converts Canvas equation images to MathJax
    - Converts LaTeX: patterns to MathJax
    - Preserves HTML tags
    - Handles multi-line content
    
    Args:
        answer_html: Raw HTML from Canvas CSV
        
    Returns:
        Cleaned HTML ready for insertion
    """
    if not answer_html or not answer_html.strip():
        return ''
    
    # Convert Canvas equation images first
    cleaned = convert_canvas_equation_images(answer_html)
    
    # Then convert any remaining "LaTeX:" patterns
    cleaned = convert_latex_in_html(cleaned)
    
    return cleaned
