# IngestLocal 🚬🗿

IngestLocal is a local desktop tool inspired by gitingest.

Because everything runs locally, it has no platform-imposed upload size limits (MB caps) and can handle large repositories directly from disk.

It works with repositories from Azure DevOps, GitHub, GitLab, Bitbucket, and similar tools, since it reads your local clone instead of depending on a specific remote provider.

It lets you select files from any local project and export a single Markdown context file containing:

- A project summary
- The directory structure
- The full content of selected files

The app is built with CustomTkinter and runs entirely on your machine.

## Features

- Visual file tree with recursive selection
- Smart exclusions for common generated folders and binary/media files
- Live preview with three panes:
	- Summary
	- Directory structure
	- Files content
- Syntax highlighting for code blocks (Pygments)
- Git metadata in summary (branch, last commit)
- One-click export to markdown in contexts/

## Tech Stack

- Python 3.12+
- CustomTkinter
- Tkinter / ttk
- Pygments

## Installation

1. Clone the repository:

```bash
git clone https://github.com/FrnndCndr/IngestLocal
cd IngestLocal
```

2. Create and activate a virtual environment:

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

From the project root:

```bash
python ingestlocal.py
```

## How To Use

1. Click Select Folder and choose a local repository or project.
2. Mark files/folders in the tree.
3. Review the generated preview panes.
4. Set an output filename (optional).
5. Click Export.

Output files are written to:

```text
contexts/
```

Default filename:

```text
git_ingest_output.md
```

## Configuration

Core behavior is configured in config.py:

- EXCLUDE_FOLDERS: folders skipped during scan
- EXCLUDE_FILES: filenames skipped during scan
- EXCLUDE_EXTENSIONS: extensions skipped during scan
- EXTENSION_LANG: extension to Markdown code fence language mapping
- CONTEXTS_DIR: export output folder
- DEFAULT_EXPORT_NAME: default exported filename

## Project Structure

```text
IngestLocal/
├── ingestlocal.py
├── config.py
├── requirements.txt
├── app/
│   ├── ui.py
│   ├── tree.py
│   ├── exporter.py
│   ├── git_info.py
│   ├── highlighter.py
│   └── __init__.py
├── contexts/
└── README.md
```

## Notes

- The application is local-only and does not upload project files.
- Very large selections can increase preview time and output size.

## License

MIT. See LICENSE for details.