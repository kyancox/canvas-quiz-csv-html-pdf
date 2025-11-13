#!/usr/bin/env python3
"""
Test script to convert Quiz 5 rubric to HTML templates.
Run this to generate HTML templates for inspection.
"""

from importlib import import_module
from core.rubric_converter import convert_rubric_to_templates, save_templates

def main():
    print("="*60)
    print("Testing Rubric Converter - Quiz 5")
    print("="*60)
    
    # Load quiz 5 config
    config_module = import_module('configs.quiz5_config')
    config = config_module.QUIZ_CONFIG
    
    # Convert rubric to templates
    templates = convert_rubric_to_templates(config)
    
    # Save templates
    print(f"\n💾 Saving templates to templates/quiz{config['quiz_id']}/")
    save_templates(templates, config['quiz_id'])
    
    print("\n" + "="*60)
    print("✅ Done! Check the following files:")
    print(f"  - templates/quiz5/q1_template.html")
    print(f"  - templates/quiz5/q2_template.html")
    print("="*60)

if __name__ == '__main__':
    main()

