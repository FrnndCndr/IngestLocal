# Folders to skip when scanning the project tree
EXCLUDE_FOLDERS = {
    '.git', '__pycache__', 'node_modules', '.venv', 'env', '.env',
    '.tox', 'build', 'dist', '.pytest_cache', '.angular',
}

# Specific filenames to skip
EXCLUDE_FILES = {
    '.env', 'package-lock.json', 'poetry.lock', 'Pipfile.lock', '.coverage',
}

# File extensions to skip (binaries, media, archives)
EXCLUDE_EXTENSIONS = {
    '.pyc', '.exe', '.dll', '.so', '.zip', '.tar', '.gz', '.rar',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf',
    '.mp3', '.mp4', '.mov', '.avi', '.flv', '.webm',
}

# Maps file extension -> markdown code fence language identifier
EXTENSION_LANG: dict[str, str] = {
    '.py':         'python',
    '.js':         'javascript',
    '.ts':         'typescript',
    '.jsx':        'jsx',
    '.tsx':        'tsx',
    '.html':       'html',
    '.css':        'css',
    '.scss':       'scss',
    '.sass':       'sass',
    '.json':       'json',
    '.yaml':       'yaml',
    '.yml':        'yaml',
    '.md':         'markdown',
    '.sql':        'sql',
    '.sh':         'bash',
    '.bash':       'bash',
    '.zsh':        'bash',
    '.cs':         'csharp',
    '.java':       'java',
    '.cpp':        'cpp',
    '.c':          'c',
    '.go':         'go',
    '.rs':         'rust',
    '.rb':         'ruby',
    '.php':        'php',
    '.xml':        'xml',
    '.toml':       'toml',
    '.ini':        'ini',
    '.tf':         'hcl',
    '.dockerfile': 'dockerfile',
    '.vue':        'vue',
    '.svelte':     'svelte',
    '.kt':         'kotlin',
    '.swift':      'swift',
}

# Output directory name (relative to cwd)
CONTEXTS_DIR = 'contexts'

# Default export filename
DEFAULT_EXPORT_NAME = 'git_ingest_output.md'