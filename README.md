# Canvas Quiz PDF System

Config-driven system for generating individual PDFs per question type per student.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Install Playwright browsers: `playwright install chromium`
3. Create config file: Copy `configs.example/quiz_config_template.py` to `configs/quizX_config.py`

## Usage

```bash
python run_quiz.py --quiz 5 --csv "path/to/quiz.csv" --limit 5
```

## Architecture

- `core/` - Generic reusable modules
- `configs/` - Quiz-specific mappings (git ignored)
- `configs.example/` - Config template
- `rubrics/` - LaTeX solution files
- `templates/` - Generated HTML templates
- `output/` - Generated PDFs

