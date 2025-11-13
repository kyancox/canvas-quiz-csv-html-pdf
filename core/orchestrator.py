"""
Orchestrator: Main workflow that ties all modules together.

Coordinates:
1. Template generation (or loading)
2. CSV parsing
3. HTML generation per student
4. PDF rendering
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional
from .rubric_converter import convert_rubric_to_templates, save_templates
from .csv_parser import CanvasCSVParser
from .html_generator import generate_student_html, load_template, sanitize_filename
from .pdf_generator import generate_pdf


def load_or_generate_templates(config: dict, force_regenerate: bool = False) -> Dict[str, str]:
    """
    Load existing templates or generate new ones from rubric.
    
    Args:
        config: Quiz configuration
        force_regenerate: If True, regenerate even if templates exist
        
    Returns:
        Dict mapping group_id → HTML template
    """
    quiz_id = config['quiz_id']
    templates_dir = Path(f"templates/quiz{quiz_id}")
    
    templates = {}
    all_exist = True
    
    # Check if templates already exist
    for group in config['question_groups']:
        template_file = templates_dir / f"{group['id']}_template.html"
        if not template_file.exists():
            all_exist = False
            break
    
    # Generate if needed
    if not all_exist or force_regenerate:
        print("📝 Generating templates from rubric...")
        templates = convert_rubric_to_templates(config)
        save_templates(templates, quiz_id)
    else:
        # Load existing templates
        print(f"📂 Loading existing templates from {templates_dir}/")
        for group in config['question_groups']:
            template_file = templates_dir / f"{group['id']}_template.html"
            templates[group['id']] = load_template(str(template_file))
            print(f"   ✓ Loaded {group['id']}_template.html")
    
    return templates


async def process_quiz(
    csv_path: str,
    config: dict,
    limit: Optional[int] = None,
    force_regenerate: bool = False
) -> None:
    """
    Main workflow: CSV → HTML → PDFs
    
    Args:
        csv_path: Path to Canvas CSV export
        config: Quiz configuration dict
        limit: Optional limit on number of students (for testing)
        force_regenerate: Force regeneration of templates
    """
    quiz_id = config['quiz_id']
    quiz_name = config['quiz_name']
    
    print("=" * 70)
    print(f"Canvas Quiz PDF Generator")
    print(f"Quiz {quiz_id}: {quiz_name}")
    print("=" * 70)
    
    # Step 1: Load or generate templates
    templates = load_or_generate_templates(config, force_regenerate)
    
    # Step 2: Parse CSV
    print(f"\n📊 Parsing CSV...")
    parser = CanvasCSVParser(csv_path, config)
    students = parser.get_student_data(limit=limit)
    
    if limit:
        print(f"   ⚠ Limited to {limit} students for testing")
    
    # Copy images to output folder for each question group
    print(f"\n📁 Setting up output directories...")
    import shutil
    for group in config['question_groups']:
        group_id = group['id']
        group_name = group['name']
        base_dir = f"output/quiz{quiz_id}/{group_id}_{group_name.lower().replace(' ', '_')}"
        
        # Copy images from templates to output
        template_images = Path(f"templates/quiz{quiz_id}/images")
        output_images = Path(f"{base_dir}/html/images")
        
        if template_images.exists():
            if output_images.exists():
                shutil.rmtree(output_images)
            shutil.copytree(template_images, output_images)
            print(f"   ✓ Copied images to {base_dir}/html/images/")
    
    # Step 3: Generate PDFs for each student
    total_pdfs = len(students) * len(config['question_groups'])
    print(f"\n📄 Generating {total_pdfs} PDFs ({len(students)} students × {len(config['question_groups'])} questions)...")
    
    pdf_count = 0
    for student_idx, student in enumerate(students, 1):
        print(f"\n  [{student_idx}/{len(students)}] {student['name']}")
        
        for group in config['question_groups']:
            group_id = group['id']
            group_name = group['name']
            
            # Generate HTML for this student + question
            print(f"    - Generating {group_id} HTML...")
            html = generate_student_html(
                templates[group_id],
                student,
                group_id
            )
            
            # Create output paths
            # Format: output/quiz5/q1_network_flow/html/q1v9_nf_Alice_Smith.html
            #         output/quiz5/q1_network_flow/pdf/q1v9_nf_Alice_Smith.pdf
            safe_name = sanitize_filename(student['name'])
            
            # Get variant number from student data
            variant = student[group_id]['variant']
            
            # Get abbreviation from quiz config (default to quiz_id if missing)
            abbr = config.get('abbr', f'q{quiz_id}')
            
            # Create variant-aware filename: q1v9_nf_Alice_Smith
            variant_filename = f"{group_id}v{variant}_{abbr}_{safe_name}"
            
            base_dir = f"output/quiz{quiz_id}/{group_id}_{group_name.lower().replace(' ', '_')}"
            html_dir = f"{base_dir}/html"
            pdf_dir = f"{base_dir}/pdf"
            
            html_path = f"{html_dir}/{variant_filename}.html"
            pdf_path = f"{pdf_dir}/{variant_filename}.pdf"
            
            # Save HTML file for debugging
            Path(html_dir).mkdir(parents=True, exist_ok=True)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"      💾 {html_path}")
            
            # Render to PDF
            print(f"    - Rendering {group_id} PDF...")
            success = await generate_pdf(html, pdf_path, html_path)
            
            if success:
                pdf_count += 1
                print(f"      ✓ {pdf_path}")
            else:
                print(f"      ✗ Failed to generate {pdf_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print(f"✅ Complete!")
    print(f"   Generated {pdf_count}/{total_pdfs} PDFs")
    print(f"   Output: output/quiz{quiz_id}/")
    print("=" * 70)

