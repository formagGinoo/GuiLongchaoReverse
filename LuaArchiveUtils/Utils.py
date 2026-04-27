import struct
import io
import os
import shutil
import re
from structures import ArchiveFileHead, ArchiveFileInfo

# === FPArchive.SimpleTextHelper START ===

KEY1 = bytes([
    26, 84, 94, 40, 155, 43, 205, 239,
    226, 164, 86, 120, 144, 59, 207, 175
])

def decrypt_bytes(data: bytes) -> bytes:
    decrypted = bytearray(data)
    for i in range(len(decrypted)):
        decrypted[i] ^= KEY1[i % len(KEY1)]
    return bytes(decrypted)

def decrypt(data: str, secret_key: str) -> str:
    data_chars = list(data)
    key_chars = list(secret_key)
    for i in range(len(data_chars)):
        data_chars[i] = chr(ord(data_chars[i]) ^ ord(key_chars[i % len(key_chars)]))
    return ''.join(data_chars)

# === FPArchive.SimpleTextHelper END ===

# === FPArchive.ArchiveSingleFile START ===

def ReadFileHead(f):
    """Read the ArchiveFileHead from the file"""
    head = ArchiveFileHead()
    name_len_bytes = f.read(4)
    (name_len,) = struct.unpack('<i', name_len_bytes)
    version_chars = f.read(name_len).decode('utf-8')
    head.version = version_chars
    head.fileCount = struct.unpack('<i', f.read(4))[0]
    head.bodySize = struct.unpack('<i', f.read(4))[0]
    head.zipFlag = struct.unpack('<H', f.read(2))[0]
    print("File Head:")
    print(head)
    return head

def ReadStartPosition(f):
    """Read the start position from the last 8 bytes of the file"""
    # Save current position
    current_pos = f.tell()
    
    # Seek to -8 bytes from end (equivalent to Seek(-8L, SeekOrigin.End))
    f.seek(-8, 2)  # 2 = SEEK_END
    
    # Read 8 bytes as long (int64)
    start_position = struct.unpack('<q', f.read(8))[0]
    
    # Restore original position
    f.seek(current_pos)
    
    return start_position

def ReadFileInfo(f, secret_key: str):
    """Read ArchiveFileInfo entries from the file"""
    file_info_list = []

    block_size = struct.unpack('<i', f.read(4))[0]
    inner_data = f.read(block_size)
    inner_stream = io.BytesIO(inner_data)

    file_count = struct.unpack('<i', inner_stream.read(4))[0]

    for _ in range(file_count):
        name_len = struct.unpack('<i', inner_stream.read(4))[0]
        raw_name_bytes = inner_stream.read(name_len)
        raw_name = ''.join([chr(b) for b in raw_name_bytes])
        decrypted_name = decrypt(raw_name, secret_key)

        pos = struct.unpack('<q', inner_stream.read(8))[0] - 356
        length = struct.unpack('<i', inner_stream.read(4))[0] // 2

        file_info = ArchiveFileInfo(decrypted_name, pos, length)
        file_info_list.append(file_info)

    return file_info_list

# === FPArchive.ArchiveSingleFile END ===


# === CUSTOM FUNCTIONS ===

def IsLuaBytecode(path):
    with open(path, "rb") as f:
        header = f.read(4)
    return header == b'\x1bLua'

def ExtractSingleFile(f, archive_file_info, start_position, text_encrypt_key):
    """
    Extract a single file from the archive, equivalent to C# method:
    
    object obj = ArchiveSingleFile.locker;
    lock (obj)
    {
        long num = this.startPosition + archiveFileInfo.pos;
        this.binReader.BaseStream.Seek(num, SeekOrigin.Begin);
        return SimpleTextHelper.DecryptBytes(this.binReader.ReadBytes(archiveFileInfo.len), LuaArchiveUtil.textEncryptKey);
    }
    """
    # Calculate position: startPosition + archiveFileInfo.pos
    actual_pos = start_position + archive_file_info.pos
    
    # Seek to the position
    f.seek(actual_pos)
    
    # Read the encrypted bytes
    encrypted_data = f.read(archive_file_info.len)
    
    # Decrypt using SimpleTextHelper.DecryptBytes equivalent
    decrypted_data = decrypt_bytes(encrypted_data)
    
    return decrypted_data

def ExtractFilesFromFolder(input_folder: str, secret_key: str, output_root="LuaArchiveExtracted"):
    for filename in os.listdir(input_folder):
        if filename.endswith('.json') or filename.endswith('.bin') or filename.endswith('.temp'):
            continue
        input_file_path = os.path.join(input_folder, filename)
        if not os.path.isfile(input_file_path):
            continue
        print(f"Processing archive: {input_file_path}")
        with open(input_file_path, "rb") as f:
            print("Reading header...")
            ReadFileHead(f)
            print("Reading file info entries...")
            files = ReadFileInfo(f, secret_key)
            print("Reading start position...")
            start_position = ReadStartPosition(f)
            print(f"Start position: {start_position}")

            print("Extracting files...")
            for entry in files:
                # Extract using the new method that matches C# implementation
                decrypted_data = ExtractSingleFile(f, entry, start_position, secret_key)

                # Use subfolder for each archive to avoid name conflicts
                archive_output_root = os.path.join(output_root, os.path.splitext(filename)[0])
                output_path = os.path.join(archive_output_root, entry.fileName)
                output_dir = os.path.dirname(output_path)
                # If a file exists where the directory should be, remove it
                if os.path.isfile(output_dir):
                    os.remove(output_dir)
                os.makedirs(output_dir, exist_ok=True)

                with open(output_path, "wb") as out_file:
                    out_file.write(decrypted_data)
                print(f"Extracted: {entry.fileName} ({entry.len} bytes)")

        print(f"Done extracting from {filename}.")
    print("All archives processed.")
    print(f"Starting merge and cleanup of extracted structure in {output_root}...")
    # After extracting all archives, merge and clean the extracted structure
    try:
        merged_path = MergeLuaArchives(output_root)
        print(f"Merge completed. Output saved to: {merged_path}")
    except Exception as e:
        print(f"Error while merging extracted folders: {e}")


def MergeLuaArchives(base_dir: str, merged_dir: str = None) -> str:
    """
    Merge extracted Lua archive folders and files with structured output.

    - Groups folders by pattern (e.g., Configs, Configs_1, Configs_2 -> configs/)
    - Renames files ending with `_json` to `.json`
    - Adds `.luac` extension to files without any suffix
    - Handles duplicate files by appending `_N` suffix

    Returns the path to the merged directory.
    """
    group_pattern = re.compile(r"^([A-Za-z]+)(?:_\d+)?$")

    # collect all top-level directories to process BEFORE creating temp dir
    top_dirs = [os.path.join(base_dir, n) for n in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, n))]

    # We'll merge into a temporary folder, then move contents into base_dir
    temp_merged = merged_dir or os.path.join(base_dir, "_merged_tmp")
    # ensure temp is clean
    if os.path.exists(temp_merged):
        shutil.rmtree(temp_merged)
    os.makedirs(temp_merged, exist_ok=True)
    # if temp created inside base_dir accidentally listed among top_dirs, exclude it
    if temp_merged in top_dirs:
        top_dirs.remove(temp_merged)

    # Build groups based on folder names
    folder_groups = {}
    for full_path in top_dirs:
        name = os.path.basename(full_path)
        match = group_pattern.match(name)
        grp = match.group(1) if match else name
        folder_groups.setdefault(grp, []).append(full_path)

    # Merge into temp_merged
    for group_name, paths in folder_groups.items():
        target_root = os.path.join(temp_merged, group_name.lower())
        for path in paths:
            for root, dirs, files in os.walk(path):
                # Compute a cleaned relative path to avoid duplicating the group folder name
                rel_path = os.path.relpath(root, path)
                if rel_path == ".":
                    rel_path = ""
                else:
                    parts = rel_path.split(os.sep)
                    # if the first component equals group_name, drop it to prevent group/group
                    if parts and parts[0].lower() == group_name.lower():
                        parts = parts[1:]
                    rel_path = os.path.join(*parts) if parts else ""

                dest_dir = os.path.join(target_root, rel_path) if rel_path else target_root
                os.makedirs(dest_dir, exist_ok=True)

                for file in files:
                    if file.endswith("_json"):
                        new_file_name = file[:-5] + ".json"
                    elif IsLuaBytecode(os.path.join(root, file)):
                        new_file_name = file + ".luac"
                    else:
                        new_file_name = file

                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dest_dir, new_file_name)

                    if os.path.exists(dst_file):
                        base_name, ext = os.path.splitext(new_file_name)
                        i = 1
                        while os.path.exists(os.path.join(dest_dir, f"{base_name}_{i}{ext}")):
                            i += 1
                        dst_file = os.path.join(dest_dir, f"{base_name}_{i}{ext}")

                    shutil.copy2(src_file, dst_file)

    # Remove original (unmerged) directories inside base_dir
    for d in top_dirs:
        try:
            shutil.rmtree(d)
        except Exception:
            pass

    # Move merged contents from temp_merged into base_dir
    for item in os.listdir(temp_merged):
        src = os.path.join(temp_merged, item)
        dst = os.path.join(base_dir, item)
        if os.path.exists(dst):
            # If dst exists (unlikely after rmtree), merge by moving children
            if os.path.isdir(src):
                for sub in os.listdir(src):
                    ssub = os.path.join(src, sub)
                    ddst = os.path.join(dst, sub)
                    if os.path.exists(ddst):
                        # find unique name
                        base_n, ext = os.path.splitext(sub)
                        i = 1
                        while os.path.exists(os.path.join(dst, f"{base_n}_{i}{ext}")):
                            i += 1
                        ddst = os.path.join(dst, f"{base_n}_{i}{ext}")
                    shutil.move(ssub, ddst)
                # remove empty src
                try:
                    os.rmdir(src)
                except Exception:
                    pass
            else:
                # file exists, rename
                base_n, ext = os.path.splitext(item)
                i = 1
                while os.path.exists(os.path.join(base_dir, f"{base_n}_{i}{ext}")):
                    i += 1
                shutil.move(src, os.path.join(base_dir, f"{base_n}_{i}{ext}"))
        else:
            shutil.move(src, dst)

    # cleanup temp
    try:
        if os.path.exists(temp_merged):
            shutil.rmtree(temp_merged)
    except Exception:
        pass

    return base_dir