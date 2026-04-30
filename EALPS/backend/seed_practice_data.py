"""
Seed practice problems into the database.
Run this after: python run.py
Then in another terminal: python seed_practice_data.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import PracticeProblem, ProblemTestCase, Skill

app = create_app()

PROBLEMS = [
    {
        'title': 'FizzBuzz',
        'description': '''
Write a program that prints integers 1 to 100, but:
- For multiples of 3, print "Fizz" instead of the number
- For multiples of 5, print "Buzz" instead of the number
- For multiples of both 3 and 5, print "FizzBuzz"

Example output:
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
...
        ''',
        'difficulty': 1,
        'languages_supported': ['python', 'javascript'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {
                'input_data': '',
                'expected_output': '1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz\n16\n17\nFizz\n19\nBuzz\nFizz\n22\n23\nFizz\nBuzz\n26\nFizz\n28\n29\nFizzBuzz\n31\n32\nFizz\n34\nBuzz\nFizz\n37\n38\nFizz\nBuzz\n41\nFizz\n43\n44\nFizzBuzz\n46\n47\nFizz\n49\nBuzz\nFizz\n52\n53\nFizz\nBuzz\n56\nFizz\n58\n59\nFizzBuzz\n61\n62\nFizz\n64\nBuzz\nFizz\n67\n68\nFizz\nBuzz\n71\nFizz\n73\n74\nFizzBuzz\n76\n77\nFizz\n79\nBuzz\nFizz\n82\n83\nFizz\nBuzz\n86\nFizz\n88\n89\nFizzBuzz\n91\n92\nFizz\n94\nBuzz\nFizz\n97\n98\nFizz\nBuzz',
                'is_hidden': False,
            },
        ],
    },
    {
        'title': 'Sum of Array',
        'description': 'Write a function that returns the sum of all elements in an array.\nInput: [1, 2, 3, 4, 5]\nOutput: 15',
        'difficulty': 1,
        'languages_supported': ['python', 'javascript'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {'input_data': '[1, 2, 3, 4, 5]', 'expected_output': '15', 'is_hidden': False},
            {'input_data': '[10, 20, 30]', 'expected_output': '60', 'is_hidden': True},
        ],
    },
    {
        'title': 'Reverse String',
        'description': 'Write a function that reverses a string.\nInput: "hello"\nOutput: "olleh"',
        'difficulty': 1,
        'languages_supported': ['python', 'javascript'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {'input_data': 'hello', 'expected_output': 'olleh', 'is_hidden': False},
            {'input_data': 'world', 'expected_output': 'dlrow', 'is_hidden': True},
        ],
    },
    {
        'title': 'Find Maximum',
        'description': 'Write a function that finds and returns the maximum element in an array.',
        'difficulty': 1,
        'languages_supported': ['python', 'javascript'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {'input_data': '[3, 7, 2, 9, 1]', 'expected_output': '9', 'is_hidden': False},
            {'input_data': '[10, 5, 20, 15]', 'expected_output': '20', 'is_hidden': True},
        ],
    },
    {
        'title': 'Check Palindrome',
        'description': 'Write a function that checks if a string is a palindrome (reads same forwards and backwards).',
        'difficulty': 2,
        'languages_supported': ['python', 'javascript'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {'input_data': 'racecar', 'expected_output': 'True', 'is_hidden': False},
            {'input_data': 'hello', 'expected_output': 'False', 'is_hidden': False},
        ],
    },
    {
        'title': 'Fibonacci Sequence',
        'description': 'Write a function that returns the first N Fibonacci numbers.\nFibonacci: 0, 1, 1, 2, 3, 5, 8, 13...',
        'difficulty': 2,
        'languages_supported': ['python', 'javascript'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {'input_data': '5', 'expected_output': '[0, 1, 1, 2, 3]', 'is_hidden': False},
            {'input_data': '7', 'expected_output': '[0, 1, 1, 2, 3, 5, 8]', 'is_hidden': True},
        ],
    },
    {
        'title': 'Basic SELECT',
        'description': 'Write a SQL query to select all users from the users table.',
        'difficulty': 1,
        'languages_supported': ['sql'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {'input_data': '', 'expected_output': "{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}\n{'id': 2, 'name': 'Bob', 'email': 'bob@example.com'}", 'is_hidden': False},
        ],
    },
    {
        'title': 'Count Occurrences',
        'description': 'Write a function that counts how many times a specific element appears in an array.',
        'difficulty': 2,
        'languages_supported': ['python', 'javascript'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {'input_data': '[1, 2, 2, 3, 2, 4], 2', 'expected_output': '3', 'is_hidden': False},
        ],
    },
    {
        'title': 'Merge Sorted Arrays',
        'description': 'Write a function that merges two sorted arrays into one sorted array.',
        'difficulty': 3,
        'languages_supported': ['python', 'javascript'],
        'time_limit': 5,
        'memory_limit': 256,
        'test_cases': [
            {'input_data': '[1, 3, 5], [2, 4, 6]', 'expected_output': '[1, 2, 3, 4, 5, 6]', 'is_hidden': False},
        ],
    },
]


def seed_problems():
    """Add practice problems to database."""
    with app.app_context():
        try:
            print('Starting to seed practice problems...')

            for prob_data in PROBLEMS:
                # Check if problem already exists
                existing = PracticeProblem.query.filter_by(title=prob_data['title']).first()
                if existing:
                    print(f'  Skipping {prob_data["title"]} (already exists)')
                    continue

                problem = PracticeProblem(
                    title=prob_data['title'],
                    description=prob_data['description'],
                    difficulty=prob_data['difficulty'],
                    languages_supported=prob_data['languages_supported'],
                    time_limit=prob_data['time_limit'],
                    memory_limit=prob_data['memory_limit'],
                )
                db.session.add(problem)
                db.session.flush()

                # Add test cases
                for tc_data in prob_data['test_cases']:
                    tc = ProblemTestCase(
                        problem_id=problem.problem_id,
                        input_data=tc_data['input_data'],
                        expected_output=tc_data['expected_output'],
                        is_hidden=tc_data.get('is_hidden', False),
                    )
                    db.session.add(tc)

                print(f'  Added: {problem.title} (difficulty {problem.difficulty})')

            db.session.commit()
            print(f'\n✓ Successfully seeded {len(PROBLEMS)} practice problems!')

        except Exception as e:
            db.session.rollback()
            print(f'✗ Error seeding problems: {str(e)}')
            raise


if __name__ == '__main__':
    seed_problems()
