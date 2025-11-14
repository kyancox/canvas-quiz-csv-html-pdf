"""
Zip creator utility for organizing quiz PDFs.
"""

import zipfile
import shutil
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()


def create_quiz_zip(quiz_id: int, output_name: Optional[str] = None) -> bool:
    """
    Create a zip file with all PDFs organized by question.
    
    Structure:
        quiz5pdfs.zip
        ├── question_1/
        │   ├── q1v1_nf_Alice_Smith.pdf
        │   └── ...
        └── question_2/
            ├── q2v1_nf_Alice_Smith.pdf
            └── ...
    
    Args:
        quiz_id: Quiz number (e.g., 5)
        output_name: Optional custom zip filename (default: quiz{id}pdfs.zip)
        
    Returns:
        True if successful, False otherwise
    """
    from importlib import import_module
    
    # Load config
    try:
        config_module = import_module(f'configs.quiz{quiz_id}_config')
        config = config_module.QUIZ_CONFIG
    except ImportError:
        return False
    
    # Determine output zip name
    if output_name is None:
        output_name = f"quiz{quiz_id}pdfs.zip"
    
    output_path = Path(f"output/{output_name}")
    quiz_output_dir = Path(f"output/quiz{quiz_id}")
    
    if not quiz_output_dir.exists():
        return False
    
    # Create temporary directory structure
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Process each question group
        total_pdfs = 0
        for idx, group in enumerate(config['question_groups'], start=1):
            group_id = group['id']
            group_name = group['name']
            
            # Find the PDF directory (handles the naming pattern)
            pdf_dir = quiz_output_dir / f"{group_id}_{group_name.lower().replace(' ', '_')}" / "pdf"
            
            if not pdf_dir.exists():
                continue
            
            # Create question folder in temp directory
            question_folder = temp_path / f"question_{idx}"
            question_folder.mkdir()
            
            # Copy all PDFs
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if not pdf_files:
                continue
            
            for pdf_file in pdf_files:
                shutil.copy2(pdf_file, question_folder / pdf_file.name)
            
            total_pdfs += len(pdf_files)
        
        if total_pdfs == 0:
            return False
        
        # Create zip file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for question_folder in sorted(temp_path.iterdir()):
                if question_folder.is_dir():
                    for pdf_file in sorted(question_folder.rglob("*.pdf")):
                        # Preserve folder structure in zip
                        arcname = pdf_file.relative_to(temp_path)
                        zipf.write(pdf_file, arcname)
        
        return True

