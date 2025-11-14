# Canvas Quiz CSV to PDF Generator

A production-ready Python system that converts Canvas LMS quiz exports (CSV format) into individual student PDFs, organized by question type for efficient TA grading.

**Built for:** CS 577: Introduction to Algorithms @ UW-Madison  
**Status:** ✅ Production-ready for Quiz 5

## Features

- ✅ **Individualized PDFs**: One PDF per question type per student
- ✅ **Variant Filtering**: Shows only the specific question variant each student received
- ✅ **Math Rendering**: Automatic Canvas equation image → MathJax conversion
- ✅ **Image Mapping**: Handles TikZ graphs with manual image mapping
- ✅ **Page Break Control**: Configurable per question (same-page or each-part)
- ✅ **Compact Styling**: LaTeX-matching format (~1 page for Q1, ~4 pages for Q2)
- ✅ **Rich CLI**: Progress bars, timing statistics, colored output
- ✅ **Generic Architecture**: Config-driven system works for all 6 quizzes

## Problem Statement

Canvas quizzes use question banks where each student receives different variants. When grading:
- **TAs need efficiency**: Grade all Q1s together, then all Q2s
- **Students see different questions**: Each PDF must show only their specific variant
- **Answers must be preserved**: HTML, LaTeX, tables, images kept exactly as submitted

## Solution Architecture

### Variant-Based Tagging System

**Key Insight:** Canvas tags parent questions, not subparts.

```
Tag [1.9] in CSV → Student received Variant 9 of Question 1
                 → Show graph9.jpg
                 → Subparts (a, b) are same for all variants
```

### Shared Subpart Columns

Canvas exports subpart answers in **shared columns** across all variants:
- **Q1 Part A**: Variant-specific (tagged column)
- **Q1 Part B**: Shared column (all variants use same column)
- **Q2 Part A**: Variant-specific (tagged column)
- **Q2 Parts B, C**: Shared columns

This means:
- Student with variant 1.9 answers Part A in column 71
- Same student answers Part B in column 16 (shared with all other Q1 variants)

### Workflow

```
1. TEMPLATE GENERATION (once per quiz)
   LaTeX Rubric → Preprocessor → Pandoc → HTML Templates
   
   - Replace TikZ with \includegraphics (if image_map provided)
   - Convert to HTML with Pandoc
   - Wrap each variant in <div data-version="N">
   - Add placeholders: {{PART_A}}, {{PART_B}}, {{PART_C}}
   
   Result: q1_template.html with ALL 12 variants
           q2_template.html with ALL 11 variants

2. CSV PARSING (per student)
   Canvas CSV → Student Data Extraction
   
   - Find tagged columns (e.g., [1.9])
   - Check Status column to determine which variant student answered
   - Extract Part A answer from tagged column
   - Extract Parts B/C from shared columns
   
   Result: {
     'name': 'Alice',
     'sisid': 'UW123',
     'q1': {'variant': 9, 'answers': {'a': '<p>6</p>', 'b': '<p>{s,t}</p>'}}
   }

3. HTML GENERATION (per student per question)
   Template + Student Data → Personalized HTML
   
   - Load template (all variants)
   - Remove all variants except student's variant
   - Replace {{PART_A}}, {{PART_B}} with student's answers
   - Convert Canvas equation images to MathJax
   - Add student header (Name, SISID, Canvas ID)
   
   Result: HTML file ready for PDF rendering

4. PDF RENDERING
   HTML → Playwright (Headless Chrome) → PDF
   
   - Load HTML from file (allows images to resolve)
   - Wait for MathJax to render equations
   - Generate PDF with proper margins and page breaks
   
   Result: output/quiz5/q1_network_flow/pdf/q1v9_nf_Alice_Smith.pdf
```

## Setup

### Prerequisites

- Python 3.8+
- Pandoc (install via homebrew: `brew install pandoc`)
- Virtual environment (recommended)

### Installation

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser
playwright install chromium

# 4. You're ready!
```

## Usage

### For Quiz 5 (Already Configured)

```bash
# Test with 3 students (fast iteration)
python run_quiz.py --quiz 5 --csv "Quiz 5 - Network Flow.csv" --limit 3

# Full production run (all 69 students, ~5 minutes)
python run_quiz.py --quiz 5 --csv "Quiz 5 - Network Flow.csv"

# Force regenerate templates (if rubric changed)
python run_quiz.py --quiz 5 --csv "Quiz 5.csv" --regenerate
```

### CLI Output

```
╭──────────────────────────────────────────╮
│  Canvas Quiz PDF Generator               │
│  Quiz 5: Network Flow                    │
╰──────────────────────────────────────────╯

📊 Parsed CSV: Quiz 5 - Network Flow...
   ✓ 69 students
   ✓ 23 question variants found
   ✓ 3 shared subpart columns

📄 Generating 138 PDFs (69 students × 2 questions)
  Processing: Alice Smith
    Avg: 4.7s/student • Est: 5m 12s remaining
  ━━━━━━━━━━━━━━━━━━━━━━━━━ 50% • 35/69

╭──────────────────────────────────────────╮
│  Summary:                                │
│    PDFs generated: 138/138               │
│    Timing:                               │
│    Total: 324s (5.4m)                    │
│    Avg per student: 4.7s                 │
╰──────────────────────────────────────────╯
```

## Adding a New Quiz (Quiz 1, Quiz 6, etc.)

### Step 1: Gather Materials

**You need:**
1. Canvas CSV export: `Quiz 6 - [Topic] Student Analysis Report.csv`
2. LaTeX rubric: `quiz6_solutions_rubric.tex`
3. Image files (if TikZ graphics are used)
4. Quiz materials zip file from course staff

### Step 2: Setup Quiz Folder

```bash
cd rubrics
mkdir quiz6
# Extract quiz materials
unzip quiz6_materials.zip -d quiz6/
# This creates: rubrics/quiz6/quiz6_solutions_rubric.tex, images/, etc.
```

### Step 3: Analyze CSV Structure

**Important:** Each quiz may have different CSV column patterns!

```bash
# Run CSV analysis
python3 << 'EOF'
import pandas as pd
import re

df = pd.read_csv('test_data/Quiz 6 - [Topic].csv')

print(f"Total students: {len(df)}")
print(f"Total columns: {len(df.columns)}\n")

# Find all tagged columns
print("Tagged columns (variant identifiers):")
for i, col in enumerate(df.columns):
    match = re.match(r'^(\d+\.\d+)', str(col).strip())
    if match:
        print(f"  Col {i}: Tag {match.group(1)} - {str(col)[:60]}")

# Search for shared subpart columns
print("\nSearching for shared subpart patterns:")
for pattern in ['Part B:', 'Part C:', 'partition', 'explain', 'describe']:
    matches = [i for i, c in enumerate(df.columns) if pattern.lower() in str(c).lower()]
    if matches:
        print(f"  '{pattern}': columns {matches[:3]}")
        print(f"    Example: {df.columns[matches[0]][:60]}")
EOF
```

**Record:**
- How many question types? (Q1, Q2, Q3?)
- How many variants per type?
- How many subparts per question?
- Which columns are shared vs variant-specific?

### Step 4: Create Config File

```bash
cp configs.example/quiz_config_template.py configs/quiz6_config.py
```

**Customize:**

```python
QUIZ_CONFIG = {
    'quiz_id': 6,
    'quiz_name': 'Dynamic Programming',  # UPDATE
    'abbr': 'dp',  # UPDATE - used in filenames
    'rubric_folder': 'quiz6',  # UPDATE
    
    'question_groups': [
        {
            'id': 'q1',
            'name': 'Knapsack',  # UPDATE
            'variant_tags': ['1.1', '1.2', '1.3', ...],  # UPDATE from CSV
            'num_parts': 2,  # UPDATE - count subparts
            'latex_line_range': (50, 700),  # UPDATE - inspect rubric
            'num_versions': 10,  # UPDATE
            'points': 5,  # UPDATE
            'page_break': 'same-page',  # UPDATE - your preference
            # Add image_map if TikZ used
        },
        # Add more question groups as needed
    ]
}
```

### Step 5: Update Shared Column Detection

**Location:** `core/csv_parser.py` → `_find_shared_subpart_columns()`

**Current (Quiz 5):**
```python
def _find_shared_subpart_columns(self) -> Dict[str, int]:
    shared = {}
    
    for col_idx, col_name in enumerate(self.df.columns):
        col_text = str(col_name).lower().strip()
        
        # Q1 Part B: "partition" question
        if 'partition' in col_text and 'minimum' in col_text:
            shared['q1_b'] = col_idx
        
        # Q2 Part B/C
        if col_text.startswith('part b:'):
            shared['q2_b'] = col_idx
        elif col_text.startswith('part c:'):
            shared['q2_c'] = col_idx
    
    return shared
```

**For Quiz 6:** Add new patterns based on CSV analysis.

**Example:**
```python
# Q3 Part B: "Bellman equation"
if 'bellman' in col_text and 'equation' in col_text:
    shared['q3_b'] = col_idx
```

### Step 6: Handle Images (If Needed)

**If rubric uses `\includegraphics`:** No action needed (automatic)

**If rubric uses TikZ:** Manual mapping required

1. Identify all TikZ figures in rubric
2. Export/screenshot each as image file (PNG or JPG)
3. Place in `rubrics/quiz6/` folder
4. Create `image_map` in config:
   ```python
   'image_map': {
       1: 'graph1.png',
       2: 'graph2.jpg',
       # Map each variant number to its image file
   }
   ```

### Step 7: Generate Templates

```bash
python test_rubric_converter.py
```

**This will:**
- Read rubric from `rubrics/quiz6/`
- Replace TikZ with images (if mapped)
- Convert LaTeX to HTML with Pandoc
- Add question wrappers and placeholders
- Save to `templates/quiz6/`

**Verify in browser:**
```bash
open templates/quiz6/q1_template.html
```

**Check:**
- All variants present (count `<div data-version=` tags)
- Images displaying
- Part A/B/C headers correct
- Placeholders exist: `{{PART_A}}`, `{{PART_B}}`, etc.
- Solutions visible

### Step 8: Test with 3 Students

```bash
python run_quiz.py --quiz 6 --csv "Quiz 6 - [Topic].csv" --limit 3
```

**Verify output:**
- Check `output/quiz6/*/html/` files in browser
- Verify correct variant shown
- Images rendering
- Student answers inserted
- Math equations rendering
- Page breaks correct

**Open PDFs:**
```bash
open output/quiz6/q1_*/pdf/*.pdf
```

### Step 9: Debug Issues

**Common problems:**

**Answers are empty:**
- Check CSV column structure changed
- Verify `_find_shared_subpart_columns()` patterns
- Print student data: add debug statements in csv_parser

**Wrong variants:**
- Check `variant_tags` list order in config
- Verify Status column detection in CSV

**Images missing:**
- Check `image_map` keys match variant numbers
- Verify image files exist and names match exactly

### Step 10: Production Run

Once verified with 3 students:

```bash
python run_quiz.py --quiz 6 --csv "Quiz 6 - [Topic].csv"
```

Expected: ~5-6 minutes for 69 students

---

## Configuration Reference

### Required Fields

```python
'quiz_id': 6,                    # Quiz number
'quiz_name': 'Topic Name',       # Descriptive name
'rubric_folder': 'quiz6',        # Folder in rubrics/
```

### Question Group Fields

```python
{
    'id': 'q1',                                    # Unique ID
    'name': 'Question Type Name',                  # For output folders
    'variant_tags': ['1.1', '1.2', ..., '1.N'],   # One per variant
    'num_parts': 2,                                # Subparts (a, b, c, etc.)
    'latex_line_range': (start, end),             # Lines in rubric .tex
    'num_versions': N,                             # Number of variants
    'points': X,                                   # Total points
    'page_break': 'same-page' | 'each-part',      # Page break behavior
    'image_map': {1: 'img1.png', 2: 'img2.jpg'}   # Optional: TikZ mapping
}
```

### Page Break Options

- **`'same-page'`**: All parts stay together (good for short answers)
  - Example: Q1 (2 parts, simple answers) → 1 page total

- **`'each-part'`**: Each part starts new page (good for long answers)
  - Example: Q2 (3 parts, detailed answers) → 4 pages total
    - Page 1: Question intro
    - Page 2: Part A (header + solution + student answer)
    - Page 3: Part B (header + solution + student answer)
    - Page 4: Part C (header + solution + student answer)

---

## File Structure

```
canvas-quiz-csv-html-pdf/
├── core/                        # Generic reusable modules
│   ├── rubric_converter.py      # LaTeX → HTML template generation
│   ├── csv_parser.py            # Extract variants and answers
│   ├── html_generator.py        # Map answers to templates
│   ├── pdf_generator.py         # Playwright PDF rendering
│   ├── latex_converter.py       # Canvas math → MathJax
│   └── orchestrator.py          # Main workflow with Rich CLI
│
├── configs/                     # Quiz-specific settings (gitignored)
│   ├── __init__.py
│   ├── quiz5_config.py          # ✅ Quiz 5 complete
│   └── quiz6_config.py          # ← Create this for Quiz 6
│
├── configs.example/             # Template and documentation
│   └── quiz_config_template.py
│
├── rubrics/                     # LaTeX rubrics and images (gitignored)
│   ├── quiz5/
│   │   ├── quiz5_solutions_rubric.tex
│   │   └── images/              # Graph images for Q1
│   └── quiz6/                   # ← Create and unzip materials here
│
├── templates/                   # Generated HTML (gitignored)
│   ├── quiz5/
│   │   ├── q1_template.html
│   │   ├── q2_template.html
│   │   └── images/
│   └── quiz6/                   # Auto-generated
│
├── test_data/                   # CSV files (gitignored)
│   ├── Quiz 5 - Network Flow Student Analysis Report.csv
│   └── Quiz 6 - [Topic] Student Analysis Report.csv  # Add here
│
├── output/                      # Generated PDFs (gitignored)
│   ├── quiz5/
│   │   ├── q1/
│   │   │   ├── html/            # For debugging
│   │   │   │   └── images/      # Copied automatically
│   │   │   └── pdf/             # For grading
│   │   │       ├── q1v1_nf_Alice_Smith.pdf
│   │   │       ├── q1v1_nf_Bob_Jones.pdf
│   │   │       └── ...
│   │   └── q2/
│   │       ├── html/
│   │       └── pdf/
│   └── quiz6/                   # Auto-generated
│
├── run_quiz.py                  # Main CLI entry point
├── test_rubric_converter.py     # Template generation tester
├── requirements.txt
├── .cursorrules                 # AI assistant context
├── .gitignore                   # Protects sensitive data
└── README.md                    # This file
```

---

## Manual Steps Required Per Quiz

### 1. Image Mapping (If TikZ Graphics)

**When needed:** Rubric contains `\begin{tikzpicture}` instead of `\includegraphics`

**Process:**
1. Open rubric PDF
2. For each question variant, identify the graph
3. Match to image filename in course materials
4. Create mapping in config:
   ```python
   'image_map': {
       1: 'graph_325.png',
       2: 'Graph_324.jpg',  # Note: Case-sensitive!
       3: 'network.png',
       # ... one entry per variant
   }
   ```

**Example (Quiz 5 Q1):**
- Variant 1 shows specific graph → `graph_325.png`
- Variant 2 shows different graph → `Graph_324.jpg`
- All 12 variants mapped individually

### 2. Shared Column Detection

**When needed:** Every quiz (subpart columns vary)

**Process:**
1. Run CSV analysis script (Step 3 above)
2. Identify column names for Parts B, C, etc.
3. Update `core/csv_parser.py` → `_find_shared_subpart_columns()`:
   ```python
   # Add patterns for Quiz 6
   if 'your_pattern_here' in col_text:
       shared['q3_b'] = col_idx
   ```

**Example patterns:**
- "partition" + "minimum cut" (Quiz 5 Q1 Part B)
- "Part B:" prefix (Quiz 5 Q2 Part B)
- "Bellman equation" (potential Quiz 4 pattern)
- "optimal substructure" (potential pattern)

### 3. Line Range Detection

**When needed:** Every quiz

**Process:**
1. Open rubric `.tex` file
2. Find where each question group starts/ends
3. Count line numbers
4. Update config:
   ```python
   'latex_line_range': (50, 800),  # Lines 50-800 for Q1
   ```

**Tips:**
- Search for `\question[X]` to find question boundaries
- Include full question including all variants
- Use `sed -n '50,800p' rubric.tex` to preview range

### 4. Page Break Preferences

**When needed:** Every quiz (your decision)

**Guidelines:**
- Short answers (1-2 sentences) → `'same-page'`
- Long answers (paragraphs) → `'each-part'`
- Mixed → Test both and decide

**Example:**
- Quiz 5 Q1: Short numerical answers → `'same-page'`
- Quiz 5 Q2: Long network descriptions → `'each-part'`

---

## Troubleshooting

### Issue: "No question variants found"

**Cause:** CSV column structure different or tags not detected

**Solution:**
1. Check CSV column headers manually
2. Verify tag format (should be X.Y at start of column)
3. Update regex in `_find_variant_columns()` if needed

### Issue: "Answers are empty"

**Cause:** Shared column patterns not matching

**Solution:**
1. Print column names: `print(df.columns[10:30])`
2. Find actual text for subpart columns
3. Update `_find_shared_subpart_columns()` with correct patterns
4. Test: `parser.shared_columns` should have entries

### Issue: "Wrong variant shown"

**Cause:** Variant detection or ordering issue

**Solution:**
1. Check `variant_tags` list order matches rubric order
2. Verify first tag corresponds to first question in rubric
3. Test with known student: print their detected variant

### Issue: "Images not rendering in PDF"

**Cause:** Image paths or missing files

**Solution:**
1. Check HTML file in browser: `open output/quiz6/q1_*/html/*.html`
2. If images show in HTML but not PDF: Playwright issue (rare)
3. If images broken in HTML: Check `image_map` and file names
4. Verify images copied: `ls output/quiz6/q1_*/html/images/`

### Issue: "Math showing as broken images"

**Cause:** Canvas equation images not converted

**Solution:**
- Check `latex_converter.py` is being called
- Verify `<img class="equation_image">` tags in student answers
- Should auto-convert to MathJax `\(...\)`
- Test: inspect HTML, should have `<span class="math inline">`

### Issue: "Page breaks not working"

**Cause:** Templates not regenerated after config change

**Solution:**
```bash
rm -rf templates/quiz6
python test_rubric_converter.py
# Then regenerate PDFs
```

### Issue: "Templates have orphaned headers"

**Cause:** LaTeX structure issue

**Solution:**
- Check rubric has consistent `\question[X]` commands
- Verify no broken LaTeX syntax
- Check `latex_line_range` includes complete questions

---

## CSV Structure Deep Dive

### Canvas Export Pattern

```
Column Pattern for Multi-Part Questions:

[Tagged Question] | EarnedPoints | Status | ItemID | ItemType | [Part B - Shared] | ...
      ^                 ^           ^         ^         ^              ^
   Part A          metadata   (detect here) metadata metadata     Part B
 (variant-          (skip)    (!=Not        (skip)    (skip)    (all variants
  specific)                   Attempted)                         use this)
```

### Example (Generic Quiz):

```
Col 11:  "1.1 What is ..."              ← Variant 1.1, Part A
Col 12:  "EarnedPoints"                 ← Skip
Col 13:  "Status"                       ← Check: not "Not Attempted"
Col 14:  "ItemID"                       ← Skip
Col 15:  "ItemType"                     ← Skip
Col 16:  "Give a ..."                   ← Part B (shared by ALL Q1 variants)
Col 17:  "EarnedPoints.1"               ← Skip
Col 18:  "Status.1"                     ← Skip
...
Col 21:  "2.10 Consider a ..."          ← Variant 2.10, Part A
...
Col 26:  "Part B: Given the ..."        ← Q2 Part B (shared)
...
Col 31:  "Part C: Given the ..."        ← Q2 Part C (shared)
```

**Key Insight:** Columns are **not sequential**! They're shuffled. Must search by pattern, not position.

---

## Performance & Scalability

### Benchmarks (Quiz 5, 69 students)

- **Per student:** 4.5-5.0 seconds (2 PDFs)
- **Total time:** ~5-6 minutes
- **PDF sizes:** 130-180KB each
- **Total output:** ~20MB for 138 PDFs

### Bottlenecks

1. **Playwright rendering:** ~2-2.5s per PDF
2. **MathJax wait time:** ~1s per PDF
3. **BeautifulSoup parsing:** <0.5s per student

### Optimization Notes

- Already async where possible
- Single Playwright instance per run
- Parallel processing not implemented (sequential is acceptable)
- Could parallelize PDF generation if needed (future)

---

## Security & Privacy

### Gitignored Files (Proprietary)

- `configs/*.py` (except `__init__.py`)
- `rubrics/` (contains solutions)
- `templates/` (derived from solutions)
- `output/` (student data)
- `test_data/` (student answers)

### Safe to Commit

- All `core/` modules (generic code)
- `configs.example/` (template only)
- Documentation files
- `.gitignore`, `.cursorrules`
- `run_quiz.py`, `test_rubric_converter.py`

---

## Tech Stack

- **Python 3.8+**: Core language
- **Pandas**: CSV parsing
- **BeautifulSoup4**: HTML manipulation
- **Pandoc**: LaTeX → HTML conversion
- **Playwright**: Headless Chrome for PDF generation
- **MathJax**: Math equation rendering in PDFs
- **Rich**: Beautiful CLI with progress bars

---

## Future Enhancements

### Potential Improvements

1. **Config-driven shared columns:**
   ```python
   'subpart_patterns': {
       'b': 'partition.*minimum',
       'c': 'optimal.*substructure'
   }
   ```
   Would eliminate need to edit `csv_parser.py`

2. **Parallel PDF generation:**
   - Current: Sequential (acceptable)
   - Future: Process multiple students simultaneously
   - Benefit: 2-3x speedup for large classes

3. **Auto-detect line ranges:**
   - Parse rubric to find `\question` boundaries
   - Eliminate manual line counting

4. **Template caching:**
   - Detect if rubric unchanged
   - Skip regeneration automatically

5. **Error recovery:**
   - Continue on single student failure
   - Generate error report at end

---

## Support

### For Quiz 6 Implementation

When you're ready to add Quiz 6:

1. Gather all materials (CSV, rubric, images)
2. Follow "Adding a New Quiz" section above
3. Use the handoff document for detailed context
4. Test with `--limit 3` first!

### Common Questions

**Q: Do I need to modify core modules?**  
A: Usually only `csv_parser.py` → `_find_shared_subpart_columns()` needs updates

**Q: How do I know if TikZ mapping is needed?**  
A: Open rubric PDF - if you see graphs, check the .tex file for `\begin{tikzpicture}`

**Q: What if Quiz 6 has 4 question types instead of 2?**  
A: Just add more question_groups in config - system handles any number

**Q: Can I change page breaks after generating PDFs?**  
A: Yes, but must regenerate: update config → delete templates → re-run

**Q: What if CSV structure is completely different?**  
A: The variant detection logic is generic, but shared column patterns may need significant updates

---

## Success Criteria

**System is working when:**
- ✅ CLI shows progress with timing
- ✅ All PDFs generate without errors
- ✅ Each PDF shows only 1 variant (not all 12)
- ✅ Correct images appear
- ✅ Student answers inserted in orange boxes
- ✅ Math equations render properly
- ✅ Page breaks match preferences
- ✅ Filenames include variant numbers
- ✅ Processing time under 15 minutes for 300 students

---

## Quick Reference Commands

```bash
# Setup new quiz
mkdir rubrics/quiz6
cd rubrics/quiz6
unzip ../../quiz6_materials.zip

# Create config
cp configs.example/quiz_config_template.py configs/quiz6_config.py
# Edit configs/quiz6_config.py

# Update shared columns (if needed)
# Edit core/csv_parser.py → _find_shared_subpart_columns()

# Generate templates
python test_rubric_converter.py

# Test with 3 students
python run_quiz.py --quiz 6 --csv "Quiz 6.csv" --limit 3

# Verify in browser
open templates/quiz6/q1_template.html
open output/quiz6/q1_*/html/*.html
open output/quiz6/q1_*/pdf/*.pdf

# Production run
python run_quiz.py --quiz 6 --csv "Quiz 6.csv"
```

---

## License & Attribution

Built for CS 577 @ UW-Madison. Quiz content and solutions are proprietary and not included in public repository.
