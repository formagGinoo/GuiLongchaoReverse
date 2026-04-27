import sys
import shutil
import subprocess
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

def main():
    if len(sys.argv) < 4:
        print("Usage: batch.py <unluac_path> <input_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)
    
    unluac_path = Path(sys.argv[1])
    in_dir = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    
    # Optional 4th argument: number of parallel workers
    if len(sys.argv) >= 5:
        try:
            workers = int(sys.argv[4])
            if workers <= 0:
                raise ValueError()
        except Exception:
            print("Invalid workers value, must be positive integer", file=sys.stderr)
            sys.exit(1)
    else:
        workers = min(32, (os.cpu_count() or 1) * 2)

    # Collect files to process
    lua_tasks, other_files = collect_files(in_dir, in_dir, out_dir)

    # Process .lua files in parallel using ThreadPoolExecutor
    if lua_tasks:
        print(f"Processing {len(lua_tasks)} .lua files with {workers} workers...")
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(process_lua, unluac_path, src, dst): (src, dst) for src, dst in lua_tasks}
            for fut in as_completed(futures):
                src, dst = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    print(f"Error processing {src}: {e}", file=sys.stderr)
    else:
        print("No .lua files found to process.")

    # Copy other files sequentially
    for src, dst in other_files:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"Error copying {src}: {e}", file=sys.stderr)

def collect_files(current_dir, base_in_dir, base_out_dir):
    """
    Recursively collect files to process.
    Returns tuple (lua_tasks, other_files) where each is a list of (src_path, dst_path).
    """
    lua_tasks = []
    other_files = []
    try:
        if not current_dir.is_dir():
            return lua_tasks, other_files

        for item in current_dir.iterdir():
            if item.name in ['.', '..']:
                continue

            if item.is_dir():
                sub_lua, sub_other = collect_files(item, base_in_dir, base_out_dir)
                lua_tasks.extend(sub_lua)
                other_files.extend(sub_other)
            else:
                # Calculate output path
                relative_dir = item.parent.relative_to(base_in_dir)
                out_path = base_out_dir / relative_dir
                item_lower = item.name.lower()
                # Process .lua and .luac files (decompile only, don't copy original .luac)
                if item_lower.endswith('.json'):
                    continue  # Skip .json files
                if item_lower.endswith('.lua') or item_lower.endswith('.luac'):
                    output_file = out_path / (item.stem + ".lua")
                    lua_tasks.append((item, output_file))
                elif item_lower.endswith('.bytes'):
                    output_file = out_path / item.name.replace('.bytes', '')
                    lua_tasks.append((item, output_file))
                else:
                    output_file = out_path / item.name
                    other_files.append((item, output_file))

    except PermissionError as e:
        print(f"Permission denied accessing {current_dir}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error processing directory {current_dir}: {e}", file=sys.stderr)

    return lua_tasks, other_files


def process_lua(unluac_path, src_path, dst_path):
    """Run unluac on a single file and write output to dst_path."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(dst_path, 'w', encoding='utf-8') as f:
            subprocess.run([
                'java', '-jar', str(unluac_path),
                '--rawstring', str(src_path)
            ], stdout=f, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error processing {src_path}: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Error writing to {dst_path}: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
