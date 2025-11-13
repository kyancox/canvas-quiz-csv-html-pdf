# Canvas Quiz PDF System

Config-driven system for generating individual PDFs per question type per student.

## Problem Statement

Canvas quizzes often have question banks where each student receives different variants (e.g., different graph parameters). When grading:
- TAs want to grade by question type (all Q1s together, then all Q2s)
- Each PDF should show only what the student saw (their specific variant)
- Student answers must be preserved exactly as submitted (HTML, LaTeX, images)

## Solution Architecture

This system generates **2 PDFs per student** (one per question type):
- `q1_network_flow/Alice_Smith.pdf` - Alice's Q1 variant + her answers + solution
- `q2_bipartite/Alice_Smith.pdf` - Alice's Q2 variant + her answers + solution

### Algorithm Flow

```
1. TEMPLATE GENERATION (once per quiz)
   LaTeX Rubric → Pandoc → HTML Templates
   
   Result: q1_template.html contains ALL 12 variants
           q2_template.html contains ALL 12 variants
           
   Each variant wrapped in: <div data-version="3">...</div>

2. CSV PARSING (per student)
   Canvas CSV → Extract:
   - Which variant they received (version number)
   - Their answers for each part (raw HTML)
   - Question tags mapping (e.g., [1.1], [2.3])
   
   Example:
   Alice: Version 3 of Q1, Version 7 of Q2
   Answers: {1.1: "<p>6</p>", 1.2: "<p>{s},{t}</p>", ...}

3. HTML GENERATION (per student per question)
   For Alice's Q1 PDF:
   - Load q1_template.html
   - Hide versions 1,2,4,5,...,12 (CSS: display: none)
   - Show ONLY version 3 (the specific graph Alice saw)
   - Replace {{ANSWER_1_1}} with Alice's HTML answer
   
4. PDF RENDERING
   HTML → Playwright/Chromium → PDF
   - Supports MathJax for equations
   - Preserves student HTML exactly
```

### Key Benefits

1. **Grading Efficiency**: TAs can grade all Q1s together, then all Q2s
2. **Focused PDFs**: Each PDF shows only what the student saw (no blank sections)
3. **Data Integrity**: Student answers never modified or parsed
4. **Scalability**: Generic system works for all 6 quizzes with just config changes

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Install Playwright browsers: `playwright install chromium`
3. **Unzip quiz materials**: Extract the quiz zip file into `rubrics/quizX/`
   ```bash
   cd rubrics
   unzip quiz5_materials.zip -d quiz5/
   # This creates: rubrics/quiz5/quiz5_solutions_rubric.tex, Q4.png, graph*.jpg, etc.
   ```
4. Create config file: Copy `configs.example/quiz_config_template.py` to `configs/quizX_config.py`
5. Update config: Set line ranges and question tags in your config file
6. **Manual image mapping** (if needed): If your rubric uses TikZ graphs instead of `\includegraphics`, add an `image_map` dictionary to map question versions to image filenames. See `configs/quiz5_config.py` for an example.

## Usage

```bash
# Test with 5 students
python run_quiz.py --quiz 5 --csv "Quiz 5 - Network Flow.csv" --limit 5

# Full run (all students)
python run_quiz.py --quiz 5 --csv "Quiz 5 - Network Flow.csv"
```

## Output Structure

```
output/
└── quiz5/
    ├── q1_network_flow/
    │   ├── Alice_Smith.pdf
    │   ├── Bob_Jones.pdf
    │   └── ...
    └── q2_bipartite_matching/
        ├── Alice_Smith.pdf
        ├── Bob_Jones.pdf
        └── ...
```

## Directory Structure

- `core/` - Generic reusable modules
- `configs/` - Quiz-specific mappings (git ignored)
- `configs.example/` - Config template
- `rubrics/` - LaTeX solution files and images
  - `rubrics/quizX/` - Unzip course materials here (contains .tex + images)
- `templates/` - Generated HTML templates
- `output/` - Generated PDFs

## Image Handling

### Automatic (Recommended)
If your LaTeX uses `\includegraphics{filename.png}`, images are automatically detected and copied.

### Manual Mapping (TikZ Graphs)
For Quiz 5 (Network Flow), the rubric uses TikZ code to draw graphs. Since TikZ doesn't convert to HTML, we manually map each question version to a pre-rendered image:

```python
'image_map': {
    1: 'graph_325.png',
    2: 'Graph_324.jpg',
    3: 'network.png',
    # ... etc
}
```

**For future quizzes:** If you have TikZ graphs, you'll need to:
1. Export/screenshot each graph as an image file
2. Add the `image_map` dictionary to your config
3. Place images in `rubrics/quizX/` folder

The converter will automatically replace TikZ code with `\includegraphics` based on this mapping.

