import subprocess
import sqlite3
import re
import tempfile
import os
from typing import Dict, List, Any


class CodeExecutor:
    """
    Executes code in Python, JavaScript, Java, C, HTML, CSS, and SQL.
    Uses subprocess with timeout protection and output capture.
    """

    @staticmethod
    def execute_python(code: str, test_cases: List[Dict], timeout: int = 5) -> Dict[str, Any]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True, text=True, timeout=timeout
                )
                stdout, stderr = result.stdout, result.stderr

                if result.returncode != 0:
                    return {
                        'success': False, 'output': stdout, 'error': stderr,
                        'execution_time': 0, 'test_results': [],
                        'status': 'runtime_error' if stderr else 'failed',
                    }

                test_results, passed_count = _check_tests(stdout, test_cases)
                status = 'passed' if not test_cases or passed_count == len(test_cases) else 'failed'
                return {
                    'success': status == 'passed', 'output': stdout, 'error': stderr,
                    'execution_time': 0, 'test_results': test_results, 'status': status,
                }

            except subprocess.TimeoutExpired:
                return _timeout_result(timeout)
            finally:
                _cleanup(temp_file)

        except Exception as e:
            return _error_result(str(e))

    @staticmethod
    def execute_javascript(code: str, test_cases: List[Dict], timeout: int = 5) -> Dict[str, Any]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['node', temp_file],
                    capture_output=True, text=True, timeout=timeout
                )
                stdout, stderr = result.stdout, result.stderr

                if result.returncode != 0:
                    return {
                        'success': False, 'output': stdout, 'error': stderr,
                        'execution_time': 0, 'test_results': [],
                        'status': 'runtime_error' if stderr else 'failed',
                    }

                test_results, passed_count = _check_tests(stdout, test_cases)
                status = 'passed' if not test_cases or passed_count == len(test_cases) else 'failed'
                return {
                    'success': status == 'passed', 'output': stdout, 'error': stderr,
                    'execution_time': 0, 'test_results': test_results, 'status': status,
                }

            except subprocess.TimeoutExpired:
                return _timeout_result(timeout)
            finally:
                _cleanup(temp_file)

        except Exception as e:
            return _error_result(str(e))

    @staticmethod
    def execute_java(code: str, test_cases: List[Dict], timeout: int = 10) -> Dict[str, Any]:
        class_match = re.search(r'public\s+class\s+(\w+)', code)
        class_name = class_match.group(1) if class_match else 'Main'

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                java_file = os.path.join(tmpdir, f'{class_name}.java')
                with open(java_file, 'w') as f:
                    f.write(code)

                # Compile
                compile_result = subprocess.run(
                    ['javac', java_file],
                    capture_output=True, text=True, timeout=timeout
                )
                if compile_result.returncode != 0:
                    return {
                        'success': False, 'output': '',
                        'error': compile_result.stderr,
                        'execution_time': 0, 'test_results': [],
                        'status': 'runtime_error',
                    }

                # Run
                try:
                    run_result = subprocess.run(
                        ['java', '-cp', tmpdir, class_name],
                        capture_output=True, text=True, timeout=timeout
                    )
                except subprocess.TimeoutExpired:
                    return _timeout_result(timeout)

                stdout, stderr = run_result.stdout, run_result.stderr
                if run_result.returncode != 0:
                    return {
                        'success': False, 'output': stdout, 'error': stderr,
                        'execution_time': 0, 'test_results': [],
                        'status': 'runtime_error',
                    }

                test_results, passed_count = _check_tests(stdout, test_cases)
                status = 'passed' if not test_cases or passed_count == len(test_cases) else 'failed'
                return {
                    'success': status == 'passed', 'output': stdout, 'error': stderr,
                    'execution_time': 0, 'test_results': test_results, 'status': status,
                }

        except FileNotFoundError:
            return _error_result('Java compiler (javac) not found — please install JDK.')
        except subprocess.TimeoutExpired:
            return _timeout_result(timeout)
        except Exception as e:
            return _error_result(str(e))

    @staticmethod
    def execute_c(code: str, test_cases: List[Dict], timeout: int = 10) -> Dict[str, Any]:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                c_file = os.path.join(tmpdir, 'main.c')
                binary = os.path.join(tmpdir, 'main')
                with open(c_file, 'w') as f:
                    f.write(code)

                # Compile
                compile_result = subprocess.run(
                    ['gcc', c_file, '-o', binary, '-lm'],
                    capture_output=True, text=True, timeout=timeout
                )
                if compile_result.returncode != 0:
                    return {
                        'success': False, 'output': '',
                        'error': compile_result.stderr,
                        'execution_time': 0, 'test_results': [],
                        'status': 'runtime_error',
                    }

                # Run
                try:
                    run_result = subprocess.run(
                        [binary],
                        capture_output=True, text=True, timeout=timeout
                    )
                except subprocess.TimeoutExpired:
                    return _timeout_result(timeout)

                stdout, stderr = run_result.stdout, run_result.stderr
                if run_result.returncode != 0:
                    return {
                        'success': False, 'output': stdout, 'error': stderr,
                        'execution_time': 0, 'test_results': [],
                        'status': 'runtime_error',
                    }

                test_results, passed_count = _check_tests(stdout, test_cases)
                status = 'passed' if not test_cases or passed_count == len(test_cases) else 'failed'
                return {
                    'success': status == 'passed', 'output': stdout, 'error': stderr,
                    'execution_time': 0, 'test_results': test_results, 'status': status,
                }

        except FileNotFoundError:
            return _error_result('C compiler (gcc) not found — please install GCC.')
        except subprocess.TimeoutExpired:
            return _timeout_result(timeout)
        except Exception as e:
            return _error_result(str(e))

    @staticmethod
    def execute_html(code: str, test_cases: List[Dict], timeout: int = 5) -> Dict[str, Any]:
        """Return HTML source for browser preview — no subprocess needed."""
        return {
            'success': True, 'output': code, 'error': '',
            'execution_time': 0, 'test_results': [], 'status': 'passed',
        }

    @staticmethod
    def execute_css(code: str, test_cases: List[Dict], timeout: int = 5) -> Dict[str, Any]:
        """Return CSS source for browser preview — no subprocess needed."""
        return {
            'success': True, 'output': code, 'error': '',
            'execution_time': 0, 'test_results': [], 'status': 'passed',
        }

    @staticmethod
    def execute_sql(sql_code: str, test_cases: List[Dict], timeout: int = 5) -> Dict[str, Any]:
        try:
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row
            conn.timeout = timeout
            cursor = conn.cursor()

            cursor.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)')
            cursor.execute('CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)')
            cursor.execute('CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, product_id INTEGER, quantity INTEGER)')
            cursor.executemany('INSERT INTO users VALUES (?, ?, ?)',
                [(1, 'Alice', 'alice@example.com'), (2, 'Bob', 'bob@example.com')])
            cursor.executemany('INSERT INTO products VALUES (?, ?, ?)',
                [(1, 'Laptop', 999.99), (2, 'Mouse', 25.99)])
            cursor.executemany('INSERT INTO orders VALUES (?, ?, ?, ?)',
                [(1, 1, 1, 1), (2, 2, 2, 2)])
            conn.commit()

            try:
                cursor.execute(sql_code)
                rows = cursor.fetchall()
                output = '\n'.join([str(dict(row)) for row in rows])
            except Exception as e:
                return _error_result(f'SQL Error: {str(e)}')

            test_results, passed_count = _check_tests(output, test_cases)
            status = 'passed' if not test_cases or passed_count == len(test_cases) else 'failed'
            conn.close()
            return {
                'success': status == 'passed', 'output': output, 'error': '',
                'execution_time': 0, 'test_results': test_results, 'status': status,
            }

        except Exception as e:
            return _error_result(str(e))

    @staticmethod
    def execute(code: str, language: str, test_cases: List[Dict], timeout: int = 5) -> Dict[str, Any]:
        dispatch = {
            'python':     CodeExecutor.execute_python,
            'javascript': CodeExecutor.execute_javascript,
            'java':       CodeExecutor.execute_java,
            'c':          CodeExecutor.execute_c,
            'html':       CodeExecutor.execute_html,
            'css':        CodeExecutor.execute_css,
            'sql':        CodeExecutor.execute_sql,
        }
        handler = dispatch.get(language)
        if not handler:
            return _error_result(f'Unsupported language: {language}')
        return handler(code, test_cases, timeout)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _check_tests(stdout: str, test_cases: List[Dict]):
    results = []
    passed = 0
    for tc in test_cases:
        expected = tc.get('expected_output', '').strip()
        actual = stdout.strip()
        ok = actual == expected
        if ok:
            passed += 1
        results.append({'input': tc.get('input_data', ''), 'expected': expected, 'actual': actual, 'passed': ok})
    return results, passed


def _timeout_result(timeout: int) -> Dict[str, Any]:
    return {
        'success': False, 'output': '',
        'error': f'Execution timeout (>{timeout}s)',
        'execution_time': timeout, 'test_results': [], 'status': 'timeout',
    }


def _error_result(msg: str) -> Dict[str, Any]:
    return {
        'success': False, 'output': '', 'error': msg,
        'execution_time': 0, 'test_results': [], 'status': 'runtime_error',
    }


def _cleanup(path: str):
    try:
        os.unlink(path)
    except Exception:
        pass
