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
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.live import Live
from .rubric_converter import convert_rubric_to_templates, save_templates
from .csv_parser import CanvasCSVParser
from .html_generator import generate_student_html, load_template, sanitize_filename
from .pdf_generator import generate_pdf

console = Console()


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
        console.print("[cyan]📝 Generating templates from rubric...[/cyan]")
        templates = convert_rubric_to_templates(config)
        save_templates(templates, quiz_id)
    else:
        # Load existing templates
        console.print(f"[cyan]📂 Loading existing templates from {templates_dir}/[/cyan]")
        for group in config['question_groups']:
            template_file = templates_dir / f"{group['id']}_template.html"
            templates[group['id']] = load_template(str(template_file))
            console.print(f"   [green]✓[/green] Loaded {group['id']}_template.html")
    
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
    
    # Display header
    header_text = f"[bold cyan]Canvas Quiz PDF Generator[/bold cyan]\n[yellow]Quiz {quiz_id}: {quiz_name}[/yellow]"
    console.print(Panel(header_text, border_style="cyan", padding=(1, 2)))
    
    # Step 1: Load or generate templates
    templates = load_or_generate_templates(config, force_regenerate)
    
    # Step 2: Parse CSV
    console.print(f"\n[cyan]📊 Parsing CSV...[/cyan]")
    parser = CanvasCSVParser(csv_path, config)
    students = parser.get_student_data(limit=limit)
    
    if limit:
        console.print(f"   [yellow]⚠ Limited to {limit} students for testing[/yellow]")
    
    # Copy images to output folder for each question group
    console.print(f"\n[cyan]📁 Setting up output directories...[/cyan]")
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
            console.print(f"   [green]✓[/green] Copied images to {base_dir}/html/images/")
    
    # Step 3: Generate PDFs for each student with progress bar
    total_pdfs = len(students) * len(config['question_groups'])
    console.print(f"\n[cyan]📄 Generating {total_pdfs} PDFs[/cyan] [dim]({len(students)} students × {len(config['question_groups'])} questions)[/dim]")
    
    pdf_count = 0
    student_times = []
    import time
    overall_start = time.time()
    
    # Create progress bar
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )
    
    with Live(progress, console=console, refresh_per_second=4):
        task_id = progress.add_task(
            "[cyan]Processing students...",
            total=len(students)
        )
        
        for student_idx, student in enumerate(students, 1):
            student_start = time.time()
            
            # Calculate running average and estimate
            if student_times:
                avg_time = sum(student_times) / len(student_times)
                remaining_students = len(students) - len(student_times)
                est_remaining = remaining_students * avg_time
                
                desc = f"[cyan]Processing: {student['name']}[/cyan]\n[dim]  Avg: {avg_time:.1f}s/student"
                if est_remaining >= 60:
                    desc += f" • Est: {est_remaining/60:.0f}m {est_remaining%60:.0f}s remaining"
                else:
                    desc += f" • Est: {est_remaining:.0f}s remaining"
                desc += "[/dim]"
            else:
                desc = f"[cyan]Processing: {student['name']}[/cyan]"
            
            progress.update(task_id, description=desc)
            
            for group in config['question_groups']:
                group_id = group['id']
                group_name = group['name']
                
                # Generate HTML for this student + question
                page_break_mode = group.get('page_break', 'same-page')
                html = generate_student_html(
                    templates[group_id],
                    student,
                    group_id,
                    page_break_mode=page_break_mode
                )
                
                # Create output paths
                safe_name = sanitize_filename(student['name'])
                variant = student[group_id]['variant']
                    
                base_dir = f"output/quiz{quiz_id}/{group_id}_{group_name.lower().replace(' ', '_')}"
                html_dir = f"{base_dir}/html"
                pdf_dir = f"{base_dir}/pdf"
                
                variant_filename = f"{group_id}v{variant}_nf_{safe_name}"
                html_path = f"{html_dir}/{variant_filename}.html"
                pdf_path = f"{pdf_dir}/{variant_filename}.pdf"
                
                # Save HTML file
                Path(html_dir).mkdir(parents=True, exist_ok=True)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                # Render to PDF
                success = await generate_pdf(html, pdf_path, html_path)
                
                if success:
                    pdf_count += 1
            
            # Track timing
            student_elapsed = time.time() - student_start
            student_times.append(student_elapsed)
            
            # Update progress
            progress.update(task_id, advance=1)
    
    # Summary with timing statistics
    console.print()
    total_time = time.time() - overall_start
    avg_time = sum(student_times) / len(student_times) if student_times else 0
    min_time = min(student_times) if student_times else 0
    max_time = max(student_times) if student_times else 0
    
    summary_text = f"""[bold cyan]Summary:[/bold cyan]
  PDFs generated: [green]{pdf_count}[/green]/[cyan]{total_pdfs}[/cyan]
  Output directory: [yellow]output/quiz{quiz_id}/[/yellow]
  
  [bold cyan]Timing:[/bold cyan]
  Total: [green]{total_time:.1f}s[/green] ({total_time/60:.1f}m)
  Avg per student: [green]{avg_time:.1f}s[/green]
  Range: [green]{min_time:.1f}s[/green] - [yellow]{max_time:.1f}s[/yellow]
  
  [dim]├── {config['question_groups'][0]['id']}_{config['question_groups'][0]['name'].lower().replace(' ', '_')}/[/dim]
  [dim]│   ├── html/ ({len(students)} files)[/dim]
  [dim]│   └── pdf/ ({len(students)} files)[/dim]
  [dim]└── {config['question_groups'][1]['id']}_{config['question_groups'][1]['name'].lower().replace(' ', '_')}/[/dim]
  [dim]    ├── html/ ({len(students)} files)[/dim]
  [dim]    └── pdf/ ({len(students)} files)[/dim]"""
    
    console.print(Panel(summary_text, border_style="green", padding=(1, 2)))

