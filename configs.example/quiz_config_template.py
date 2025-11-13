"""
Template for quiz configuration - copy to configs/quizX_config.py and customize.

This file shows the structure but does not contain real question tags.
"""

QUIZ_CONFIG = {
    'quiz_id': 5,  # Quiz number (1-6)
    'quiz_name': 'Network Flow',  # Descriptive name
    'rubric_file': 'quiz5_solutions_rubric.tex',  # LaTeX file in rubrics/
    
    'question_groups': [
        {
            'id': 'q1',  # Unique identifier for this question group
            'name': 'Network Flow',  # Descriptive name for output folder
            'tags': ['1.1', '1.2'],  # Canvas question tags [X.Y]
            'latex_line_range': (45, 671),  # Line range in rubric file
            'num_versions': 12,  # Number of question variants
            'points': 3  # Total points for this question
        },
        {
            'id': 'q2', 
            'name': 'Bipartite Matching',
            'tags': ['2.1', '2.2', '2.3'],
            'latex_line_range': (703, 1202),
            'num_versions': 12,
            'points': 6
        }
    ]
}

