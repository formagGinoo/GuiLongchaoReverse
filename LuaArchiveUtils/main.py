from Utils import ReadFileHead, ReadFileInfo, ReadStartPosition
import os

# EXAMPLE CODE FOR READING ARCHIVE HEAD AND INFO

file_path = "" # Specify the path to your file here

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    print("Please check if the file path is correct.")
else:
    print(f"File found: {file_path}")
    try:
        with open(file_path, "rb") as f:
            print("Reading file head...")
            head = ReadFileHead(f)
            
            print("Reading file info...")
            file_infos = ReadFileInfo(f, "hasdfeg@#$%9892^&^") #SimpleTextHelper.textEncryptKey
            
            print("Reading start position...")
            start_position = ReadStartPosition(f)
            
            print(f"Start position: {start_position}")
            print(f"Number of files: {len(file_infos)}")
            
            for i, info in enumerate(file_infos[:5]):  # Show first 5 files only
                print(f"File {i+1}: {vars(info)}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

