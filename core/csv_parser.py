"""
CSV Parser: Extract student data and question mappings from Canvas exports.

Parses Canvas "Student Analysis Report" CSV files to extract:
- Question tags from column headers
- Student answers (raw HTML)
- Which question version each student received
"""

import pandas as pd
import re
from typing import Dict, List, Optional
from pathlib import Path


class CanvasCSVParser:
    """
    Parse Canvas quiz CSV exports and map student answers to question groups.
    """
    
    def __init__(self, csv_path: str, config: dict):
        """
        Initialize parser with CSV file and quiz configuration.
        
        Args:
            csv_path: Path to Canvas CSV export
            config: Quiz configuration dict
        """
        self.csv_path = csv_path
        self.config = config
        self.df = pd.read_csv(csv_path)
        self.question_columns = self._identify_question_columns()
        
        print(f"\n📊 Parsed CSV: {Path(csv_path).name}")
        print(f"   - {len(self.df)} students")
        print(f"   - {len(self.question_columns)} tagged questions found")
    
    def _extract_tag_from_text(self, text: str) -> Optional[str]:
        """
        Extract [X.Y] tag from question text.
        
        Examples:
            "[1.1] What is the value..." → "1.1"
            "Question text [2.3] with tag" → "2.3"
            "No tag here" → None
        """
        if not isinstance(text, str):
            return None
        
        match = re.search(r'\[(\d+\.\d+)\]', text)
        return match.group(1) if match else None
    
    def _map_tag_to_group(self, tag: str) -> Optional[str]:
        """
        Find which question group this tag belongs to.
        
        Args:
            tag: Question tag like "1.1" or "2.3"
            
        Returns:
            Group ID (e.g., "q1") or None
        """
        for group in self.config['question_groups']:
            if tag in group['tags']:
                return group['id']
        return None
    
    def _identify_question_columns(self) -> List[Dict]:
        """
        Scan CSV columns to find tagged questions.
        
        Returns:
            List of dicts with: {
                'tag': '1.1',
                'column_name': 'full column text',
                'column_index': 15,
                'group_id': 'q1',
                'status_column': 'Status' or 'Status.1', etc.
            }
        """
        question_cols = []
        
        for idx, col_name in enumerate(self.df.columns):
            tag = self._extract_tag_from_text(col_name)
            
            if tag:
                group_id = self._map_tag_to_group(tag)
                
                if group_id:
                    # Find corresponding Status column
                    # Pattern: question column, then EarnedPoints, then Status
                    status_col = None
                    if idx + 2 < len(self.df.columns):
                        potential_status = self.df.columns[idx + 2]
                        if 'Status' in str(potential_status):
                            status_col = potential_status
                    
                    question_cols.append({
                        'tag': tag,
                        'column_name': col_name,
                        'column_index': idx,
                        'group_id': group_id,
                        'status_column': status_col
                    })
        
        return question_cols
    
    def _determine_question_version(self, row: pd.Series, group_id: str) -> int:
        """
        Determine which version of a question group the student received.
        
        Canvas exports separate columns for each variant, but they all have
        the same tag (e.g., [1.1]). We detect the version by finding which
        set of tag questions has Status != "Not Shown".
        
        Strategy:
        1. Group question columns by tag (e.g., all [1.1] columns together)
        2. For each tag group, find which occurrence was shown to student
        3. The occurrence number = version number
        
        Args:
            row: Student's row from CSV
            group_id: Question group ID (e.g., 'q1')
            
        Returns:
            Version number (1-12) or None if not found
        """
        # Get all questions for this group, grouped by tag
        group_questions = [q for q in self.question_columns if q['group_id'] == group_id]
        
        # Group by tag (may have multiple columns per tag if question bank used)
        tag_groups = {}
        for q in group_questions:
            tag = q['tag']
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(q)
        
        # For each tag, find which occurrence was shown
        # Use the first tag (e.g., 1.1) to determine version
        first_tag = sorted(tag_groups.keys())[0]
        tag_questions = tag_groups[first_tag]
        
        for idx, question in enumerate(tag_questions, start=1):
            status_col = question['status_column']
            if status_col and pd.notna(row.get(status_col)):
                status = str(row[status_col])
                if status != 'Not Shown' and status != 'not shown':
                    # This is the version they received
                    return idx
        
        return None
    
    def _extract_student_answers(self, row: pd.Series, group_id: str) -> Dict[str, str]:
        """
        Extract all answers for a specific question group.
        
        Returns:
            Dict mapping tag → answer HTML
            Example: {'1.1': '<p>6</p>', '1.2': '<p>{s},{t}</p>'}
        """
        answers = {}
        
        for question in self.question_columns:
            if question['group_id'] == group_id:
                tag = question['tag']
                col_name = question['column_name']
                status_col = question['status_column']
                
                # Check if this question was shown to the student
                if status_col and pd.notna(row.get(status_col)):
                    status = str(row[status_col])
                    if status != 'Not Shown' and status != 'not shown':
                        # Extract answer
                        answer = row.get(col_name, '')
                        if pd.notna(answer):
                            answers[tag] = str(answer)
                        else:
                            answers[tag] = ''  # Blank answer
        
        return answers
    
    def get_student_data(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Extract data for all students (or limited subset).
        
        Returns:
            List of student dicts: [{
                'name': 'Alice Smith',
                'id': '12345',
                'q1': {
                    'version': 3,
                    'answers': {'1.1': '<p>6</p>', '1.2': '<p>...</p>'}
                },
                'q2': { ... }
            }, ...]
        """
        students = []
        df_subset = self.df.head(limit) if limit else self.df
        
        for idx, row in df_subset.iterrows():
            student = {
                'name': str(row['Name']),
                'id': str(row['ID']) if pd.notna(row.get('ID')) else '',
            }
            
            # Process each question group
            for group in self.config['question_groups']:
                group_id = group['id']
                
                # Determine which version they got
                version = self._determine_question_version(row, group_id)
                
                # Extract their answers
                answers = self._extract_student_answers(row, group_id)
                
                student[group_id] = {
                    'version': version if version else 1,  # Default to 1 if not found
                    'answers': answers
                }
            
            students.append(student)
        
        return students
    
    def print_student_summary(self, student: Dict) -> None:
        """Print a summary of one student's data (for debugging)."""
        print(f"\n  Student: {student['name']}")
        for group_id in ['q1', 'q2']:
            if group_id in student:
                data = student[group_id]
                print(f"    {group_id}: Version {data['version']}")
                for tag, answer in data['answers'].items():
                    answer_preview = answer[:50] + '...' if len(answer) > 50 else answer
                    answer_preview = answer_preview.replace('\n', ' ')
                    print(f"      [{tag}]: {answer_preview}")

