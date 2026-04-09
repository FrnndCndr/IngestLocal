import os
import subprocess


def get_git_info(path: str) -> dict:
    """
    Reads branch name and latest commit info from the git repo at `path`.
    Returns a dict with available fields; empty dict if path is not a repo.

    Keys (all optional):
        branch       - current branch name
        commit_hash  - short 7-char hash
        commit_msg   - first line of commit message (ASCII-safe)
        commit_date  - formatted date string (YYYY-MM-DD HH:MM)
    """
    info = {}

    try:
        branch = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if branch.returncode == 0:
            info['branch'] = branch.stdout.strip()

        log = subprocess.run(
            ['git', 'log', '-1', '--format=%H|%s|%ad', '--date=format:%Y-%m-%d %H:%M'],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'LC_ALL': 'C.UTF-8'},
        )
        if log.returncode == 0 and log.stdout.strip():
            parts = log.stdout.strip().split('|', 2)
            info['commit_hash'] = parts[0][:7]                          if len(parts) > 0 else ''
            info['commit_msg']  = _to_ascii(parts[1])                   if len(parts) > 1 else ''
            info['commit_date'] = parts[2]                              if len(parts) > 2 else ''

    except Exception:
        pass

    return info


def _to_ascii(text: str) -> str:
    """Strips non-ASCII characters to avoid encoding issues in the summary."""
    return text.encode('ascii', errors='ignore').decode('ascii')