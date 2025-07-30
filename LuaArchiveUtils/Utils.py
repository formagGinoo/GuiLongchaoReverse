import struct
import io
import os
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

def ExtractFilesFromFolder(input_folder: str, secret_key: str, output_root="output"):
    for filename in os.listdir(input_folder):
        if filename.endswith('.json') or filename.endswith('.bin'):
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
