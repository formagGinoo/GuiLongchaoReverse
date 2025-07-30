class ArchiveFileHead:
    def __init__(self, version='', fileCount=0, bodySize=0, zipFlag=0):
        self.version = version
        self.fileCount = fileCount
        self.bodySize = bodySize
        self.zipFlag = zipFlag

    def __str__(self):
        return f"Version: {self.version}, FileCount: {self.fileCount}, BodySize: {self.bodySize}, ZipFlag: {self.zipFlag}"

class ArchiveFileInfo:
    def __init__(self, fileName='', pos=0, length=0):
        self.fileName = fileName
        self.pos = pos
        self.len = length

    def __str__(self):
        return f"FileName: {self.fileName}, Pos: {self.pos}, Len: {self.len}"
