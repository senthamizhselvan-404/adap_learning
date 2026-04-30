# EALPS Practice IDE - Setup & Usage Guide

## Backend Setup

### 1. Initialize Database
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Seed Practice Problems
```bash
python seed_practice_data.py
```

This creates 9 sample problems across difficulty levels:
- **Beginner**: FizzBuzz, Sum Array, Reverse String, Find Max
- **Easy**: Check Palindrome, Count Occurrences
- **Medium**: Fibonacci, Merge Sorted Arrays
- **SQL**: Basic SELECT query

### 3. Start Backend
```bash
python run.py
# Running on http://localhost:5000
```

---

## Frontend Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
npm run dev
# Running on http://localhost:5173
```

---

## Using the Practice IDE

### Navigation
1. Login with credentials:
   - Email: `learner@ealps.dev`
   - Password: `learner123`

2. Click **Practice** in the navigation bar

### Solving Problems
1. **Select a Problem** from the left sidebar
2. **Filter by Difficulty** (Beginner → Expert)
3. **Choose Language** (Python, JavaScript, or SQL)
4. **Write Code** in the editor
5. **Run Code** to test (won't save)
6. **Submit Solution** when ready (saves and validates all tests)

### Features
- **Real-time Execution**: See immediate feedback on your code
- **Multi-language Support**: Python, JavaScript, SQL
- **Test Validation**: See which tests pass/fail
- **Auto-skill Unlock**: Completing problems unlocks next skill in pathway
- **Progress Tracking**: View all practice sessions

---

## API Endpoints

### Practice Problems
```
GET    /api/v1/practice/problems/              List all problems
GET    /api/v1/practice/problems/{id}          Get problem details
POST   /api/v1/practice/problems/{id}/execute  Run code (no save)
POST   /api/v1/practice/problems/{id}/submit   Submit solution
```

### Practice Sessions
```
GET    /api/v1/practice/sessions/              List sessions
GET    /api/v1/practice/sessions/{id}          Get session details
```

### Admin Management
```
POST   /api/v1/admin/practice/problems         Create problem
GET    /api/v1/admin/practice/problems         List problems
PATCH  /api/v1/admin/practice/problems/{id}    Update problem
DELETE /api/v1/admin/practice/problems/{id}    Delete problem
```

---

## Code Execution Details

### Python
- Uses subprocess with timeout protection
- Supports standard library functions
- No external dependencies allowed for security

### JavaScript
- Requires Node.js on server
- Executes in Node.js environment
- Supports console.log() output

### SQL
- Uses SQLite in-memory database
- Pre-populated with sample data:
  - `users` table: id, name, email
  - `products` table: id, name, price
  - `orders` table: id, user_id, product_id, quantity

---

## Problem Structure

Each practice problem includes:
- **Title & Description**: Problem requirements
- **Difficulty Level**: 1-5 (Beginner to Expert)
- **Languages**: Supported languages for the problem
- **Test Cases**: Visible examples + hidden validation tests
- **Time/Memory Limits**: 5s timeout, 256MB memory by default
- **Skill Link** (optional): Links to a skill in the learning pathway

---

## Example Problem Creation (Admin)

```json
{
  "title": "Sum Array",
  "description": "Write a function that returns the sum of all array elements.",
  "difficulty": 2,
  "skill_id": "skill_uuid_here",
  "languages_supported": ["python", "javascript"],
  "time_limit": 5,
  "memory_limit": 256,
  "test_cases": [
    {
      "input_data": "[1, 2, 3]",
      "expected_output": "6",
      "is_hidden": false
    },
    {
      "input_data": "[10, 20, 30]",
      "expected_output": "60",
      "is_hidden": true
    }
  ]
}
```

POST to: `http://localhost:5000/api/v1/admin/practice/problems`

---

## Architecture

### Database Models
- `PracticeProblem` - Problem metadata
- `ProblemTestCase` - Test cases per problem
- `ProblemSolution` - Learner submissions
- `PracticeSession` - Aggregated practice metrics

### Code Execution
- **Safe sandboxing** via subprocess timeout
- **No network access** (PIPE only)
- **Resource limits** (5s timeout, 256MB memory)
- **Rate limiting** applied on API

### Integration
- **Pathway Auto-unlock**: Solving problems auto-unlocks next skill
- **Session Tracking**: Track hours, accuracy, progress
- **JWT Protected**: All endpoints require authentication

---

## Troubleshooting

### "Code execution failed"
- Check if Python/Node.js is installed on server
- Verify code doesn't exceed timeout (5s default)
- Check for syntax errors in submitted code

### "Problem not found"
- Ensure problem was created and seeded
- Run `python seed_practice_data.py` in backend folder

### "Editor not loading"
- Check if Monaco CDN is accessible
- Open browser console for errors
- Try refreshing the page

### "Submission not saving"
- Verify database is running (check `/health` endpoint)
- Check JWT token is valid
- Look for errors in backend logs

---

## Future Enhancements

1. **Judge0 Integration** - Offload execution to external service
2. **Collaborative Coding** - Real-time pair programming
3. **Hint System** - Tiered hints for stuck learners
4. **Leaderboards** - Fastest solve times, most problems solved
5. **Problem Analytics** - Track which problems learners struggle with
6. **Code Review** - Admin peer review of solutions
