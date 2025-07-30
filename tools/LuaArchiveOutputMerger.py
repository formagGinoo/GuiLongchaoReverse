import os
import shutil
import re

# Set your base directory here
base_dir = r""
merged_dir = os.path.join(base_dir, "_merged")  # output folder for cleaned structure

# Create merged output directory
os.makedirs(merged_dir, exist_ok=True)

# Pattern to group folders (e.g., Configs, Configs_1, Configs_2, etc.)
group_pattern = re.compile(r"^([A-Za-z]+)(?:_\d+)?$")

# Collect folder groups
folder_groups = {}

for name in os.listdir(base_dir):
    full_path = os.path.join(base_dir, name)
    if os.path.isdir(full_path):
        match = group_pattern.match(name)
        if match:
            group_name = match.group(1)
            folder_groups.setdefault(group_name, []).append(full_path)

# Merge folders
for group_name, paths in folder_groups.items():
    target_root = os.path.join(merged_dir, group_name.lower())
    for path in paths:
        for root, dirs, files in os.walk(path):
            rel_path = os.path.relpath(root, path)
            dest_dir = os.path.join(target_root, rel_path)
            os.makedirs(dest_dir, exist_ok=True)
            for file in files:
                # Rename _json -> .json
                if file.endswith("_json"):
                    new_file_name = file[:-5] + ".json"
                else:
                    new_file_name = file
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_dir, new_file_name)

                # Handle potential duplicates
                if os.path.exists(dst_file):
                    base, ext = os.path.splitext(new_file_name)
                    i = 1
                    while os.path.exists(os.path.join(dest_dir, f"{base}_{i}{ext}")):
                        i += 1
                    dst_file = os.path.join(dest_dir, f"{base}_{i}{ext}")
                
                shutil.copy2(src_file, dst_file)

print("Merge completed. Output saved to:", merged_dir)
