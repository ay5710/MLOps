import pytest
import re
import subprocess

from datetime import datetime


LOG_SEPARATOR = " - "
MIN_PARTS_WITH_MOVIE_ID = 3  # Timestamp - Level - MovieID - Message
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S,%f"
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')


def test_main_script(movie_id='0097874'):
    """Tests that main.py runs successfully and produces no errors in its log entries after the test starts, for a given movie."""
    test_start_time = datetime.now()
    test_start_time_str = test_start_time.strftime(LOG_TIMESTAMP_FORMAT)
    print(f"Test started at: {test_start_time_str} for movie_id: {movie_id}")

    try:
        # Add movie to the db
        command_add_movie = ['python', '-m', 'src.utils.manage_movies', '--add', movie_id]
        subprocess.run(command_add_movie, check=True)
        
        # Run main script
        command_main_script = ['python', 'main.py', '--movie_id', movie_id]
        result = subprocess.run(command_main_script, capture_output=True, text=True, check=True)
        full_output = result.stdout + result.stderr

        # Remove movie from the db
        command_remove_movie = ['python', '-m', 'src.utils.manage_movies', '--remove', movie_id]
        subprocess.run(command_remove_movie, check=True)

        # Identify error messages in the log
        relevant_log_entries = []
        for line in full_output.splitlines():
            cleaned_line = ANSI_ESCAPE.sub('', line)  # Remove ANSI color codes
            parts = cleaned_line.split(LOG_SEPARATOR)

            try:
                log_timestamp_str = parts[0]
                log_time = datetime.strptime(log_timestamp_str, LOG_TIMESTAMP_FORMAT)

                # Filter log messages published after the test start
                if log_time >= test_start_time:
                    # Filter log messages with a matching movie_id
                    if len(parts) >= MIN_PARTS_WITH_MOVIE_ID and parts[2].strip() == movie_id:
                        relevant_log_entries.append(line)

            except Exception as e:
                print(f"Parsing failed for log entry {line}: {e}")

        relevant_log_output = "\n".join(relevant_log_entries)
        print(f"Found {len(relevant_log_output)} relevant log entries")

        error_keywords = ["error", "failed", "exception", "traceback"]
        for keyword in error_keywords:
            assert keyword.lower() not in relevant_log_output.lower()

        assert True

    except subprocess.CalledProcessError as e:
        pytest.fail(f"main.py failed with error: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
