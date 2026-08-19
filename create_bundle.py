import os
import fnmatch
import re
from pathlib import Path

# ============================================================================
# Universal Project Bundler - Ultra Slim Version
# ============================================================================
# 1. 强力去除注释 & 空行
# 2. [新增] 限制单个文件大小 (MAX_FILE_SIZE_KB)
# 3. [新增] 自动忽略 .min.js, .map 等非源码文件
# 4. [新增] 显示每个文件的大小，方便排查
# ============================================================================

OUTPUT_FILE = "project_num.txt"

# --- 核心压缩配置 ---
REMOVE_COMMENTS = True
REMOVE_EMPTY_LINES = True

# [关键设置] 单个文件允许的最大体积 (KB)
# 超过这个大小的文件通常是库文件或数据，不是手写代码，建议跳过
MAX_FILE_SIZE_KB = 100 

# --- 包含的文件类型 ---
FILE_TYPES_TO_INCLUDE = [
    "*.py", "*.md", "*.html", "*.ts", "*.tsx", "*.cpp", "*.bat", "*.sh", "*.h", "*.json", 
    "*.css", "*.js", "*.vue", "*.jsx", "*.json", "*.example", "*.txt"

]

# --- 强制排除的目录 ---
DIRECTORIES_TO_EXCLUDE = [
    "__pycache__", ".git", ".vscode", "venv", ".venv", "bin", "obj",
    "node_modules", "dist", "dist-tools", "emsdk", "doc", "docs", "task", "tasks", 
    "build", "public", "assets", "images", "img", "fonts", "coverage", "cpp", "wiki_cache", "src-tauri","archive","Doc"
]

# --- 强制排除的具体文件 ---
FILES_TO_EXCLUDE = [
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "metadata.json", ".DS_Store", "create_bundle.py", "src/data/passives.json",OUTPUT_FILE, "README.md"
]

# --- 总是忽略的后缀 (通常是二进制或压缩后的代码) ---
ALWAYS_IGNORE_EXTENSIONS = [
    ".min.js", ".min.css", ".map", ".svg", ".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf"
]

HEADER_ANCHOR_PATTERN = "Copyright (C)"
HEADER_END_PATTERN = "# along with this program.  If not, see <https://www.gnu.org/licenses/>."

def get_file_size_kb(path: Path) -> float:
    return path.stat().st_size / 1024

def remove_comments_and_clean(content: str, file_ext: str) -> str:
    """去除注释逻辑"""
    if not REMOVE_COMMENTS: return content

    # Group A: C-Style (JS, TS, C++, CSS, etc)
    if file_ext in ['.c', '.cpp', '.h', '.hpp', '.cs', '.java', '.js', '.jsx', '.ts', '.tsx', '.css', '.json', '.less', '.scss', '.vue']:
        pattern = re.compile(
            r'(`(?:[^`\\]|\\.)*`|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(/\*[\s\S]*?\*/|//.*)', re.MULTILINE
        )
        def replacer(match):
            if match.group(2): return "" 
            return match.group(1) or match.group(0)
        content = re.sub(pattern, replacer, content)

    # Group B: Python, Shell, YAML
    elif file_ext in ['.py', '.sh', '.yaml', '.yml', '.dockerfile']:
        pattern = re.compile(
            r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|(#.*)', re.MULTILINE
        )
        def replacer(match):
            if match.group(2): return "" 
            return match.group(1) or match.group(0)
        content = re.sub(pattern, replacer, content)

    # Group C: HTML
    elif file_ext in ['.html', '.xml', '.svg']:
        content = re.sub(r'<!--[\s\S]*?-->', '', content)

    # Group D: Bat
    elif file_ext in ['.bat', '.cmd']:
        lines = [line for line in content.splitlines() if not line.strip().upper().startswith(("REM ", "::"))]
        content = "\n".join(lines)

    return content

def remove_empty_lines_func(text: str) -> str:
    if not REMOVE_EMPTY_LINES: return text
    return "\n".join([line for line in text.splitlines() if line.strip()])

def process_header_removal(text: str) -> str:
    if not HEADER_ANCHOR_PATTERN: return text
    lines = text.splitlines()
    processed_lines = []
    is_skipping = False
    header_found = False
    for line in lines:
        stripped = line.strip()
        if is_skipping:
            if stripped == HEADER_END_PATTERN: is_skipping = False
            continue
        if not header_found and HEADER_ANCHOR_PATTERN in line:
            header_found = True
            is_skipping = True
            if stripped == HEADER_END_PATTERN: is_skipping = False
            continue
        processed_lines.append(line)
    return "\n".join(processed_lines)

def main():
    print("=========================================================")
    print("  Universal Project Bundler (Size Optimized)")
    print("=========================================================")
    
    project_root = Path(__file__).resolve().parent
    output_path = project_root / OUTPUT_FILE
    
    if output_path.exists():
        try: output_path.unlink()
        except: pass

    # 动态排除
    if OUTPUT_FILE not in FILES_TO_EXCLUDE: FILES_TO_EXCLUDE.append(OUTPUT_FILE)

    all_files_to_bundle = []
    seen_paths = set()

    print("--- Scanning files... ---")
    skipped_count = 0
    skipped_size = 0

    for root, dirs, files in os.walk(project_root, topdown=True):
        dirs[:] = [d for d in dirs if d not in DIRECTORIES_TO_EXCLUDE]
        current_dir = Path(root)
        
        for file in files:
            # 1. 检查强制排除列表
            if file in FILES_TO_EXCLUDE: continue
            
            # 2. 检查特定后缀 (如 .min.js)
            if any(file.endswith(ext) for ext in ALWAYS_IGNORE_EXTENSIONS): continue

            path = current_dir / file
            
            # 3. 检查文件类型匹配
            if any(fnmatch.fnmatch(file, pattern) for pattern in FILE_TYPES_TO_INCLUDE):
                # 4. [核心优化] 检查文件大小
                size_kb = get_file_size_kb(path)
                if size_kb > MAX_FILE_SIZE_KB:
                    print(f"Skipping large file (> {MAX_FILE_SIZE_KB}KB): {file} ({size_kb:.2f} KB)")
                    skipped_count += 1
                    skipped_size += size_kb
                    continue

                if path.resolve() not in seen_paths:
                    all_files_to_bundle.append(path)
                    seen_paths.add(path.resolve())

    print(f"\n--- Bundling {len(all_files_to_bundle)} files... ---")
    total_output_size = 0

    with open(output_path, "w", encoding="utf-8") as bundle_file:
        for file_path in sorted(all_files_to_bundle):
            relative_path = file_path.as_posix()
            
            # 打印当前文件大小，帮助排查
            original_size = get_file_size_kb(file_path)
            print(f"[{original_size:6.2f} KB] Processing: {relative_path}")

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as source_file:
                    content = source_file.read()

                content = process_header_removal(content)
                content = remove_comments_and_clean(content, file_path.suffix)
                content = remove_empty_lines_func(content)

                # 写入 Bundle
                header = f"# === FILE: {relative_path} ===\n"
                bundle_file.write(header)
                if content:
                    bundle_file.write(content + "\n")
                bundle_file.write("\n") # 每个文件后留一个空行分隔
                
                total_output_size += len(content.encode('utf-8'))

            except Exception as e:
                print(f"Error: {e}")

    final_size_mb = total_output_size / (1024 * 1024)
    print(f"\n---------------------------------------------------------")
    print(f"  Result: {final_size_mb:.2f} MB")
    print(f"  Skipped {skipped_count} large files (Total saved: {skipped_size/1024:.2f} MB)")
    print(f"  Saved to: {output_path.resolve()}")
    print(f"---------------------------------------------------------")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()