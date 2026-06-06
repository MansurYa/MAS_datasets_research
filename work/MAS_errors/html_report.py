"""Генерация HTML summary report для всех исследований."""

from __future__ import annotations

import sys
import json
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[2] / ".."
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from work.MAS_errors.study_runner.run_all import RESULTS_CSV, ROW_FIELDS


def generate_html_report(output_path: Path | None = None) -> Path:
    """Сгенерировать HTML summary report."""
    if not RESULTS_CSV.exists():
        raise FileNotFoundError(f"results.csv not found: {RESULTS_CSV}")

    df = pd.read_csv(RESULTS_CSV)

    # Ensure all expected columns exist
    for col in ROW_FIELDS:
        if col not in df.columns:
            df[col] = None

    df = df[ROW_FIELDS]

    # Generate HTML
    html = _generate_html(df)
    html_path = output_path or (RESULTS_CSV.parent / "summary.html")

    with open(html_path, "w") as f:
        f.write(html)

    return html_path


def _generate_html(df: pd.DataFrame) -> str:
    """Генерировать HTML content."""
    datasets = sorted(df["dataset"].dropna().unique())
    error_types = sorted(df["error_type"].dropna().unique())
    statuses = sorted(df["status"].dropna().unique())

    table_rows = _generate_table_rows(df)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MAS Errors Summary Report</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        .filters {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .filter-group label {{
            font-weight: 500;
            color: #555;
        }}
        .filter-group select {{
            padding: 6px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
        }}
        .stats {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            font-size: 12px;
            color: #777;
            text-transform: uppercase;
        }}
        .export-btn {{
            padding: 8px 16px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }}
        .export-btn:hover {{
            background: #45a049;
        }}
        .table-wrapper {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
            cursor: pointer;
            user-select: none;
            position: sticky;
            top: 0;
        }}
        th:hover {{
            background: #e9ecef;
        }}
        th .sort-icon {{
            margin-left: 5px;
            opacity: 0.5;
        }}
        th.sorted .sort-icon {{
            opacity: 1;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}
        .status-ACCEPT {{
            background: #d4edda;
            color: #155724;
        }}
        .status-REJECT {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-UNDERPOWERED {{
            background: #fff3cd;
            color: #856404;
        }}
        .status-ERROR {{
            background: #f8d7da;
            color: #721c24;
        }}
        .dist-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            background: #e3f2fd;
            color: #1565c0;
        }}
        .thumbnail {{
            width: 80px;
            height: 60px;
            object-fit: contain;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .no-image {{
            width: 80px;
            height: 60px;
            background: #f0f0f0;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: #999;
        }}
        .error-type {{
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .study-link {{
            color: #1565c0;
            text-decoration: none;
        }}
        .study-link:hover {{
            text-decoration: underline;
        }}
        tr.hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>MAS Errors Summary Report</h1>

        <div class="filters">
            <div class="filter-group">
                <label>Dataset:</label>
                <select id="dataset-filter">
                    <option value="">All</option>
                    {"".join(f'<option value="{d}">{d}</option>' for d in datasets)}
                </select>
            </div>
            <div class="filter-group">
                <label>Error Type:</label>
                <select id="error-type-filter">
                    <option value="">All</option>
                    {"".join(f'<option value="{e}">{e}</option>' for e in error_types)}
                </select>
            </div>
            <div class="filter-group">
                <label>Status:</label>
                <select id="status-filter">
                    <option value="">All</option>
                    {"".join(f'<option value="{s}">{s}</option>' for s in statuses)}
                </select>
            </div>
            <button class="export-btn" onclick="exportFiltered()">Export Filtered CSV</button>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-value" id="total-studies">{len(df)}</div>
                <div class="stat-label">Total Studies</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="accept-count">{len(df[df["status"] == "ACCEPT"])}</div>
                <div class="stat-label">ACCEPT</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="reject-count">{len(df[df["status"] == "REJECT"])}</div>
                <div class="stat-label">REJECT</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="underpowered-count">{len(df[df["status"] == "UNDERPOWERED"])}</div>
                <div class="stat-label">UNDERPOWERED</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="error-count">{len(df[df["status"] == "ERROR"])}</div>
                <div class="stat-label">ERROR</div>
            </div>
        </div>

        <div class="table-wrapper">
            <table id="study-table">
                <thead>
                    <tr>
                        <th data-col="0" onclick="sortTable(0)">Study ID <span class="sort-icon">↕</span></th>
                        <th data-col="1" onclick="sortTable(1)">Dataset <span class="sort-icon">↕</span></th>
                        <th data-col="2" onclick="sortTable(2)">Error Type <span class="sort-icon">↕</span></th>
                        <th data-col="8" onclick="sortTable(8)">Status <span class="sort-icon">↕</span></th>
                        <th data-col="9" onclick="sortTable(9)">Distribution <span class="sort-icon">↕</span></th>
                        <th data-col="10" onclick="sortTable(10)">p-value <span class="sort-icon">↕</span></th>
                        <th data-col="7" onclick="sortTable(7)">N Errors <span class="sort-icon">↕</span></th>
                        <th data-col="15" onclick="sortTable(15)">Branch <span class="sort-icon">↕</span></th>
                        <th data-col="12" onclick="sortTable(12)">Duration <span class="sort-icon">↕</span></th>
                        <th onclick="sortTable(-1)">Thumbnail</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let sortCol = -1;
        let sortAsc = true;

        function sortTable(col) {{
            if (sortCol === col) {{
                sortAsc = !sortAsc;
            }} else {{
                sortCol = col;
                sortAsc = true;
            }}

            const table = document.getElementById('study-table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            // Update header styling
            table.querySelectorAll('th').forEach(th => th.classList.remove('sorted'));
            table.querySelectorAll(`th[data-col="${{col}}"]`)[0]?.classList.add('sorted');

            rows.sort((a, b) => {{
                if (col === -1) return 0;
                const aVal = a.cells[col]?.textContent || '';
                const bVal = b.cells[col]?.textContent || '';

                // Try numeric comparison
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return sortAsc ? aNum - bNum : bNum - aNum;
                }}

                // String comparison
                return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }});

            rows.forEach(row => tbody.appendChild(row));
        }}

        function applyFilters() {{
            const dataset = document.getElementById('dataset-filter').value;
            const errorType = document.getElementById('error-type-filter').value;
            const status = document.getElementById('status-filter').value;

            const rows = document.querySelectorAll('#study-table tbody tr');
            let visibleCount = 0;

            rows.forEach(row => {{
                const rowDataset = row.cells[1]?.textContent || '';
                const rowErrorType = row.cells[2]?.textContent || '';
                const rowStatus = row.cells[3]?.textContent || '';

                const show = (!dataset || rowDataset === dataset) &&
                           (!errorType || rowErrorType === errorType) &&
                           (!status || rowStatus === status);

                row.classList.toggle('hidden', !show);
                if (show) visibleCount++;
            }});

            document.getElementById('total-studies').textContent = visibleCount;
        }}

        function exportFiltered() {{
            const visibleRows = document.querySelectorAll('#study-table tbody tr:not(.hidden)');
            const headers = Array.from(document.querySelectorAll('#study-table th'))
                .map(th => th.textContent.replace(/\\s+↕/, '').trim())
                .filter((_, i) => i < 22); // Exclude thumbnail column

            let csv = headers.join(',') + '\\n';

            visibleRows.forEach(row => {{
                const cells = Array.from(row.cells).slice(0, 22);
                const values = cells.map(cell => {{
                    let text = cell.textContent || '';
                    if (text.includes(',')) {{
                        text = '"' + text + '"';
                    }}
                    return text;
                }});
                csv += values.join(',') + '\\n';
            }});

            const blob = new Blob([csv], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'filtered_results.csv';
            a.click();
            URL.revokeObjectURL(url);
        }}

        // Attach filter listeners
        document.getElementById('dataset-filter').addEventListener('change', applyFilters);
        document.getElementById('error-type-filter').addEventListener('change', applyFilters);
        document.getElementById('status-filter').addEventListener('change', applyFilters);
    </script>
</body>
</html>"""
    return html


def _generate_table_rows(df: pd.DataFrame) -> str:
    """Генерировать строки таблицы."""
    rows = []
    for _, row in df.iterrows():
        study_id = row.get("study_id", "")
        dataset = row.get("dataset", "")
        error_type = row.get("error_type", "")
        status = row.get("status", "")
        final_dist = row.get("final_dist", "")
        p_final = row.get("p_final", "")
        n_errors = row.get("n_errors", "")
        branch = row.get("branch", "")
        duration = row.get("duration_s", "")

        # Format p-value
        try:
            p_final_str = f"{float(p_final):.4f}" if p_final else ""
        except (ValueError, TypeError):
            p_final_str = str(p_final) if p_final else ""

        # Format duration
        try:
            duration_str = f"{float(duration):.2f}s" if duration else ""
        except (ValueError, TypeError):
            duration_str = str(duration) if duration else ""

        # Find thumbnail
        study_dir = _find_study_dir(study_id)
        png_path = None
        if study_dir:
            png_files = list(study_dir.glob("*.png"))
            if png_files:
                png_path = png_files[0]

        rows.append(f"""<tr>
            <td><a class="study-link" href="#">{study_id}</a></td>
            <td>{dataset}</td>
            <td class="error-type">{error_type}</td>
            <td><span class="status-badge status-{status}">{status}</span></td>
            <td><span class="dist-badge">{final_dist or 'N/A'}</span></td>
            <td>{p_final_str}</td>
            <td>{n_errors}</td>
            <td>{branch or ''}</td>
            <td>{duration_str}</td>
            <td>{"<img class='thumbnail' src='" + png_path.relative_to(RESULTS_CSV.parent).as_posix() + "' alt='plot'>" if png_path else '<div class=no-image>No plot</div>'}</td>
        </tr>""")

    return "\n".join(rows)


def _find_study_dir(study_id: str) -> Path | None:
    """Найти директорию исследования по study_id."""
    parsers_dir = RESULTS_CSV.parent / "parsers"
    if not parsers_dir.exists():
        return None

    # Search for directory with matching study_id
    for dataset_dir in parsers_dir.iterdir():
        if not dataset_dir.is_dir():
            continue
        for error_dir in dataset_dir.iterdir():
            if not error_dir.is_dir():
                continue
            for study_dir in error_dir.iterdir():
                if study_dir.is_dir() and study_dir.name == study_id:
                    return study_dir

    return None


def main() -> None:
    """Главная точка входа."""
    # Output to same directory as results.csv (MAS_errors/)
    html_path = generate_html_report()
    print(f"HTML report generated: {html_path}")


if __name__ == "__main__":
    main()