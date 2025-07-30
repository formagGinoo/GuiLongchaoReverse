# GuiLongchaoReverse

**GuiLongchao** ([归龙潮](https://glc.haowancheng.cn/)) Reverse Engineering Project

---

## ⚠️ Disclaimer

This project is intended **solely for educational and research purposes**.  
All rights to the original game, its code, and content belong to their respective owners.

---

## ©️ Credits

- [XLuaDumper](https://github.com/fengberd/xLuaDumper) by [fengberd](https://github.com/fengberd)
- [Check Op Codes](https://bbs.kanxue.com/thread-250618.htm) mentioned in [fengberd](https://github.com/fengberd) [article](https://blog.berd.moe/archives/xlua-reverse-note/)

---

## 📚 Table of Contents

1. [Dumping IL2CPP](#1-dumping-il2cpp)
2. [Completely Lost](#2-completely-lost)
3. [HybridCLR](#3-hybridclr)  
4. [LuaArchive](#4-luaarchive)  
5. [Lua Bytecode](#5-lua-bytecode)

---

## 1. Dumping IL2CPP

The game uses a common and straightforward process to restrict reverse engineers and data miners from understanding the game assembly structure or dumping data. At first glance, `global-metadata.dat` looked like a standard file due to its magic bytes: `AF 1B B1 FA`:

<img width="595" height="177" alt="image" src="https://github.com/user-attachments/assets/578aff58-0265-4901-a3d9-44388c2b296f" />

However, that was not the case. Tools like [Il2CppDumper](https://github.com/Perfare/Il2CppDumper) or [Il2CppInspectorRedux](https://github.com/LukeFZ/Il2CppInspectorRedux) failed to dump anything and reported that `global-metadata.dat` was encrypted or obfuscated.  So I started looking into it by attempting a memory dump during runtime. Using [x64dbg](https://x64dbg.com/) and [Scylla](https://github.com/x64dbg/Scylla), I successfully dumped `global-metadata.dat` from memory and while I was at it, I also dumped `GameAssembly.dll`. With this i was able to use [Il2CppDumper](https://github.com/Perfare/Il2CppDumper) and get my hands on `dump.cs`.

---

## 2. Completely Lost
Initially i wanted to dump lua bytecode of the game. I already knew that the game uses XLua, and so i had to hook `xluaL_loadbuffer` or `luaL_loadbuffer` and dump lua, but know to do that? Well [frida-il2cpp-bridge](https://github.com/vfsfitvnm/frida-il2cpp-bridge) exists, so lets try with that!

Script:
```ts
Il2Cpp.perform(() => {
    Il2Cpp.domain.assembly("Assembly-CSharp").image.class("XLua.LuaDLL").method("luaL_loadbuffer").implementation = function(...a){
        //public static int luaL_loadbuffer(IntPtr L, string buff, string name)
        //@ts-ignore
        console.log("[method_ptr]", a[0].field("method_ptr").value)
        console.log("[luaL_loadbuffer] lua script name: ",a[2])
        console.log("[luaL_loadbuffer] lua script buff: ",a[1])
        //@ts-ignore
        var ret = this.method("luaL_loadbuffer").invoke(...a)
    }
});
```
Output:
```shell
Script error: il2cpp: couldn't resolve export il2cpp_get_corlib
    at apply (node_modules/frida-il2cpp-bridge/dist/exports.ts:543)
    at initialize (node_modules/frida-il2cpp-bridge/dist/module.ts:64)
    at perform (node_modules/frida-il2cpp-bridge/dist/perform.ts:6)
    at <anonymous> (index.ts:47)
```

Ah! Well they obfuscated the exports table, just have to find the functions, get the offset and do as its said in [frida-il2cpp-bridge](https://github.com/vfsfitvnm/frida-il2cpp-bridge) source code comments. Right [here](https://github.com/vfsfitvnm/frida-il2cpp-bridge/blob/18cb9bea203c333366c456482c32dc64fe54c1e9/lib/exports.ts#L18). So i ended up in a situation where i had to find all the il2cpp exports. Wow, not a 5 minutes task, so i prefered to try something else and have this as last resort. Looking into IDA, dump.cs and game files, i found out that the game uses [HybridCLR](https://hybridclr.doc.code-philosophy.com/en/) but the C# assemblies did not looked that good: 

<img width="598" height="275" alt="image" src="https://github.com/user-attachments/assets/4f70bb55-4f45-4ae7-8f82-01c99065897f" />
 
So i started to take a look inside dump.cs, and here is what i found:
```csharp
// Namespace: HybridCLR
public class AESEncryption // TypeDefIndex: 15277
{
	// Fields
	private static byte[] _key1; // 0x0

	// Methods

	// RVA: 0x17EDB40 Offset: 0x17EC140 VA: 0x7FFC5E42DB40
	public static byte[] AESDecrypt(byte[] cipherText, string strKey) { }

	// RVA: 0x17EDDD0 Offset: 0x17EC3D0 VA: 0x7FFC5E42DDD0
	private static void .cctor() { }
}
```
Well well well, this `public static byte[] AESDecrypt(byte[] cipherText, string strKey) { }` method is really interesting, especially what it returns. So i setuped in IDA a break point on the return, and for my luck it reached. I had under my nose, the decrypted bytes of one of the .dll's and also `string strKey`. Known the structs:
<table>
  <tr>
    <th>System_String_o (strKey)</th>
    <th>System_String_Fields</th>
    <th>System_Byte_array (decryptedText)</th>
  </tr>
  <tr>
    <td>
      <pre><code>
        struct System_String_o 
        {
          System_String_c *klass;
          void *monitor;
          System_String_Fields fields;
        }
      </code></pre>
    </td>
    <td>
      <pre><code>
        struct System_String_Fields 
        {
          int32_t _stringLength;
          uint16_t _firstChar;
          // padding byte
          // padding byte
        }
      </code></pre>
    </td>
        <td>
      <pre><code>
        struct System_Byte_array 
        {
          Il2CppObject obj;
          Il2CppArrayBounds *bounds;
          il2cpp_array_size_t max_length;
          uint8_t m_Items[65535];
          // padding byte
        }
      </code></pre>
    </td>
  </tr>
</table>

and the register where they where stored, i could, during runtime, dump the decryption key and the decrypted assemblies. Here is the python script used for dumping the decrypted assemblies:
```python
import idaapi
import idc
import struct
import os

# === CONFIG ===
REG_NAME = "rbx"
FILENAME = "random_name.dll"

# Structure Offsets
OFFSET_MAX_LENGTH = 0x18  # il2cpp_array_size_t (uint64)
OFFSET_ITEMS = 0x20       # m_Items start

# === MAIN ===
array_ptr = idc.get_reg_value(REG_NAME)

if array_ptr == idc.BADADDR or array_ptr == 0:
    print(f"[-] Invalid pointer in {REG_NAME}")
else:
    print(f"[+] System.Byte[] pointer: 0x{array_ptr:X}")

    # Read max_length
    raw_len = idaapi.dbg_read_memory(array_ptr + OFFSET_MAX_LENGTH, 8)
    if not raw_len:
        print("[-] Failed to read max_length")
    else:
        max_length = struct.unpack("<Q", raw_len)[0]
        print(f"[+] max_length: {max_length} bytes")

        # Read m_Items
        data = idaapi.dbg_read_memory(array_ptr + OFFSET_ITEMS, max_length)
        if not data:
            print("[-] Failed to read m_Items data")
        else:
            output_path = os.path.join(idaapi.get_user_idadir(), FILENAME)
            with open(output_path, "wb") as f:
                f.write(data)
            print(f"[+] Dumped to {output_path}")
```
For the decrypt key, its the same things, read the memory based on the struct, decode the bytes into UTF-16 and you will have the key. Please find a way to get it yourself. ^_~

---

## 3. HybridCLR

Now we had readable C# assemblies, that could be loaded in tools like [dnSpy](https://github.com/dnSpyEx/dnSpy) or [ILSpy](https://github.com/icsharpcode/ILSpy). But i didn't like how i dumped them, and also if they are updated in the future, i don't want to dump them again in runtime using IDA. So the first thing i did is search for any hint of a `AESDecrypt` method inside those assemblies, in search of the same algorith they used to decrypt the dlls. Another bit of luck hit me, i found a similar method, inside Funplus.Archive.dll.
```csharp
public static byte[] AESDecrypt(byte[] cipherText, string strKey)
{
  SymmetricAlgorithm symmetricAlgorithm = Rijndael.Create();
  symmetricAlgorithm.Key = Encoding.UTF8.GetBytes(strKey);
  symmetricAlgorithm.IV = AESEncryption._key1;
  new byte[cipherText.Length];
  MemoryStream memoryStream = new MemoryStream(cipherText);
  CryptoStream cryptoStream = new CryptoStream(memoryStream, symmetricAlgorithm.CreateDecryptor(), CryptoStreamMode.Read);
  byte[] array = new byte[200];
  MemoryStream memoryStream2 = new MemoryStream();
  int num;
  while ((num = cryptoStream.Read(array, 0, array.Length)) > 0)
  {
    memoryStream2.Write(array, 0, num);
  }
  byte[] array2 = memoryStream2.ToArray();
  cryptoStream.Close();
  memoryStream.Close();
  return array2;
}
```
and with that also the AES IV :
```csharp
private static byte[] _key1 = new byte[]
{
  18, 52, 86, 120, 144, 171, 205, 239, 18, 52,
  86, 120, 144, 171, 205, 239
};
```
Known the AES algorith, the KEY and the IV, i could statically decrypt the assemblies. You can find the script i used [here](https://github.com/formagGinoo/GuiLongchaoReverse/blob/e413fe4abeac176a67f38c37bd5b005f8bd8499a/tools/HybridCLRDecrypt.py).

---

## 4. LuaArchive

Now that i had c# assemblies, i could finally focus on how files inside `game\GuiLongchao_Data\PersistentPath\Patch\Lua` are loaded into the game. If you take a look at them in a Hex-Editor, you can see that they does not seems to be lua bytecode at first glance. Well they are more than that. They are actually custom archives, which inside does not only have lua scripts but also game tables, datas and more. The logic to parse this files is stored in `Funplus.Archive.dll`. I got lost many times trying to follow how they read this files. But here is how they do that. The archives before the actually content of the file as an header, splitted in `ArchiveFileHead` and `ArchiveFileInfo`:
<table>
  <tr>
    <th>ArchiveFileHead</th>
    <th>ArchiveFileInfo</th>
  </tr>
  <tr>
    <td>
      <pre><code>
    	public class ArchiveFileHead
    	{
    		public string version;
    		public int bodySize;
    		public int fileCount;
    		public ushort zipFlag;
    		public int crc;
    	}
      </code></pre>
    </td>
    <td>
      <pre><code>
      public class ArchiveFileInfo
      {
        public string fileName;
        public long pos;
        public int len;
        public int crc;
      }
      </code></pre>
    </td>
  </tr>
</table>

and respectfully they are read file this:
<table>
  <tr>
    <th>ReadFileHead</th>
    <th>ReadFileInfo</th>
  </tr>
  <tr>
    <td>
      <pre><code>
      public void ReadFileHead(BinaryReader br)
      {
        this.luaArchiveFileHead = new ArchiveFileHead();
        int num = br.ReadInt32();
        char[] array = br.ReadChars(num);
        this.luaArchiveFileHead.version = new string(array);
        this.luaArchiveFileHead.fileCount = br.ReadInt32();
        this.luaArchiveFileHead.bodySize = br.ReadInt32();
        this.luaArchiveFileHead.zipFlag = br.ReadUInt16();
      }
      </code></pre>
    </td>
    <td>
      <pre><code>
  		public void ReadFileInfo(BinaryReader br)
  		{
  			int num = br.ReadInt32();
  			BinaryReader binaryReader = new BinaryReader(new MemoryStream(br.ReadBytes(num)), Encoding.UTF8);
  			int num2 = binaryReader.ReadInt32();
  			for (int i = 0; i < num2; i++)
  			{
  				ArchiveFileInfo archiveFileInfo = new ArchiveFileInfo();
  				int num3 = binaryReader.ReadInt32();
  				char[] array = binaryReader.ReadChars(num3);
  				archiveFileInfo.fileName = SimpleTextHelper.Decrypt(array, LuaArchiveUtil.textEncryptKey);
  				archiveFileInfo.pos = binaryReader.ReadInt64() - 356L;
  				archiveFileInfo.len = binaryReader.ReadInt32() / 2;
  			}
  		}
      </code></pre>
    </td>
  </tr>
</table>

As you can see there is an helper called `SimpleTextHelper` that decrypt the filename using a key, so called `textEncryptKey`. The decrypt algorith is this as follows:
```csharp
public static string Decrypt(char[] data, string secretKey)
{
  char[] array = secretKey.ToCharArray();
  for (int i = 0; i < data.Length; i++)
  {
    int num = i;
    data[num] ^= array[i % array.Length];
  }
  return new string(data);
}
```
I reimplemented everything in python, and this what the result was:
```shell
File found: C:\Program Files (x86)\haowancheng\GuiLongchaoBili\game\GuiLongchao_Data\PersistentPath\Patch\Lua\Xlualibs.bytes
Reading file head...
File Head:
Version: 1.0.0.0, FileCount: 4, BodySize: 0, ZipFlag: 1
Reading file info...
Number of files: 4
File 1: {'fileName': 'xlualibs/perf/memory', 'pos': 0, 'len': 565}
File 2: {'fileName': 'xlualibs/perf/profiler', 'pos': 565, 'len': 6061}
File 3: {'fileName': 'xlualibs/tdr/tdr', 'pos': 6626, 'len': 4237}
File 4: {'fileName': 'xlualibs/xlua/util', 'pos': 10863, 'len': 10063}
```
Nice. Now we know the position of each file in the archive and their length, but still, how do i read them? Are they encrypted? Well we actually know the startPosition of the archive content, and its set in the method `public bool Read(string strFileName)` after reading `ArchiveFileHead` and `ArchiveFileInfo`:
```csharp
bool flag;
try
{
  this.fsRead = new FileStream(strFileName, FileMode.Open, FileAccess.Read);
  if (this.fsRead != null)
  {
    this.binReader = new BinaryReader(this.fsRead, Encoding.UTF8);
    this.ReadFileHead(this.binReader);
    this.ReadFileInfo(this.binReader);
    this.binReader.BaseStream.Seek(-8L, SeekOrigin.End);
    this.startPosition = this.binReader.ReadInt64(); <--- HERE!!
    flag = true;
  }
  else
  {
    Logger.LogError("open file:" + strFileName + ",failed!");
    flag = false;
  }
}
catch (Exception ex) { ... }
```
So we add this pieace of imformation in the reimplementation and we manage to get this:
```shell
File found: C:\Program Files (x86)\haowancheng\GuiLongchaoBili\game\GuiLongchao_Data\PersistentPath\Patch\Lua\Xlualibs.bytes
Reading file head...
File Head:
Version: 1.0.0.0, FileCount: 4, BodySize: 0, ZipFlag: 1
Reading file info...
Start position: 169
Number of files: 4
File 1: {'fileName': 'xlualibs/perf/memory', 'pos': 0, 'len': 565}
File 2: {'fileName': 'xlualibs/perf/profiler', 'pos': 565, 'len': 6061}
File 3: {'fileName': 'xlualibs/tdr/tdr', 'pos': 6626, 'len': 4237}
File 4: {'fileName': 'xlualibs/xlua/util', 'pos': 10863, 'len': 10063}
```
The last step is to find how each file is read. Well, easy, we just need to take a look at `public byte[] ReadFile(string strFileName)`:
```csharp
public byte[] ReadFile(string strFileName)
{
ArchiveFileInfo archiveFileInfo;
if (this.luaArchiveFileInfoDicts.TryGetValue(strFileName, out archiveFileInfo))
{
  try
  {
    object obj = ArchiveSingleFile.locker;
    lock (obj)
    {
      long num = this.startPosition + archiveFileInfo.pos;
      this.binReader.BaseStream.Seek(num, SeekOrigin.Begin);
      return SimpleTextHelper.DecryptBytes(this.binReader.ReadBytes(archiveFileInfo.len), LuaArchiveUtil.textEncryptKey);
    }
  }
  catch (Exception ex)
  {
    Logger.LogError(string.Concat(new string[] { "read file:", strFileName, ",", ex.Message, " error!" }));
    return null;
  }
}
Logger.LogError("read file:" + strFileName + " not find in dicts!");
return null;
}
```
As we can see, each file startPosition is set based on the archiveContent startPosition + archiveFileInfo.pos, so for example, the `file: xlualibs/xlua/util which is at pos: 10863, starts at 169 + 10863 = 11032`. Then there is `SimpleTextHelper.DecryptBytes` that use the same key as erlier (even though this time the key is useless, seems like a placeholder), and looks like this:
```csharp
public static byte[] DecryptBytes(byte[] data, string secretKey)
{
  for (int i = 0; i < data.Length; i++)
  {
    int num = i;
    data[num] ^= SimpleTextHelper._key1[i % SimpleTextHelper._key1.Length];
  }
  return data;
}
```
And with that we successfully managed to extract and decrypt all the files inside each LuaArchive. You can find my reimplementation with some usefull methods to extract each file, [here](https://github.com/formagGinoo/GuiLongchaoReverse/tree/7f9e90c91134e625cd3a9694199aae0ba35e2492/LuaArchiveUtils). I also included `SimpleTextHelper.textEncryptKey` this time. (PS: Im not that evil ^_~)

---

## 5. Lua Bytecode

Finally we have some Lua bytecode of the scripts used in the game, probably not all the scripts, some are surely inside some assetbundles. The lua version used by the game is `5.1.5`, also confirmed by the bytecode magic header: `LuaQ`. There is not any sort of custom header, like the one used in `Xlua - Lua 5.3.5`, but the developers swapped the order on the OPCODES, and maybe made also something else. How do i know that? Well, by using a pretty helpul tool [XLuaDumper](https://github.com/fengberd/xLuaDumper/tree/master). This tool was made for a xlua.dll that used `Lua 5.3.5`, so i had to change the functions used, and their arguments:
- from `luaL_loadfilex(lua_State * L, const char* file, const char* mode)` to `luaL_loadfile(lua_State * L, const char* file)`
- from `lua_dump(lua_State * L, lua_Writer writer, void* data, int strip)` to `lua_dump(lua_State * L, lua_Writer writer, void* data)`

With this, i can hook those functions from the game xlua.dll and lua51.dll to generate Lua bytecode, then like its explained also in the article by the author of the tool ([link](https://blog.berd.moe/archives/xlua-reverse-note/)) i could compare the opcodes of the bytecodes generated by xlua.dll and by lua51.dll. My current compare script is this one:
```python
import struct

# Original opcode names
ori_op_name = [
    'MOVE', 'LOADK', 'LOADBOOL', 'LOADNIL', 'GETUPVAL', 'GETGLOBAL', 'GETTABLE',
    'SETGLOBAL', 'SETUPVAL', 'SETTABLE', 'NEWTABLE', 'SELF', 'ADD', 'SUB', 'MUL',
    'DIV', 'MOD', 'POW', 'UNM', 'NOT', 'LEN', 'CONCAT', 'JMP', 'EQ', 'LT', 'LE',
    'TEST', 'TESTSET', 'CALL', 'TAILCALL', 'RETURN', 'FORLOOP', 'FORPREP',
    'TFORLOOP', 'SETLIST', 'CLOSE', 'CLOSURE', 'VARARG'
]

# Define the header size (adjust if necessary)
HEADER_SIZE = 12

# Read the original Lua bytecode (lua5.1.luac)
with open("lua51.luac", "rb") as fp:
    ori_data = fp.read()[HEADER_SIZE:]  # Skip the header

# Read the dumped xLua bytecode (xlua.luac)
with open("xlua.luac", "rb") as fp:
    data = fp.read()[HEADER_SIZE:]  # Skip the header

# Compare byte by byte and map opcodes
new_op = {}
min_length = min(len(ori_data), len(data))

for i in range(min_length):
    by_ori = ori_data[i]
    by_new = data[i]
    
    if by_ori != by_new:
        op_idx_ori = by_ori & 0x3F  # Extract opcode bits
        op_idx_new = by_new & 0x3F  # Extract opcode bits
        
        if op_idx_ori < len(ori_op_name):
            op_name = ori_op_name[op_idx_ori]
            new_op[op_name] = op_idx_new

# Print the results
print("old \t new \t name")
for idx, op_name in enumerate(ori_op_name):
    tmp = ''
    if op_name in new_op:
        tmp = new_op[op_name]
    print(f"{idx}\t{tmp}\t{op_name}")

# Log unknown opcodes
unknown_opcodes = [idx for idx in range(len(ori_op_name)) if ori_op_name[idx] not in new_op]
if unknown_opcodes:
    print("\nUnknown Opcodes:")
    for idx in unknown_opcodes:
        print(f"Unknown opcode: {idx} - {ori_op_name[idx]}")
```

with this output:
```shell
old      new     name
0       24      MOVE
1       2       LOADK
2       1       LOADBOOL
3       5       LOADNIL
4       1       GETUPVAL
5       2       GETGLOBAL
6       0       GETTABLE
7       6       SETGLOBAL
8       2       SETUPVAL
9       0       SETTABLE
10      2       NEWTABLE
11      0       SELF
12      3       ADD
13      2       SUB
14      0       MUL
15      4       DIV
16      4       MOD
17      1       POW
18      0       UNM
19      1       NOT
20      2       LEN
21      2       CONCAT
22      63      JMP
23      1       EQ
24      2       LT
25      1       LE
26      0       TEST
27      0       TESTSET
28      2       CALL
29      2       TAILCALL
30      1       RETURN
31      62      FORLOOP
32      63      FORPREP
33      0       TFORLOOP
34      2       SETLIST
35              CLOSE
36      0       CLOSURE
37      0       VARARG

Unknown Opcodes:
Unknown opcode: 35 - CLOSE
```

Something is off, and i can't figure it out. Please help meeeeee!! ＞﹏＜

You can find Lua Binary via XLua [here](https://github.com/formagGinoo/GuiLongchaoReverse/blob/df230e5044b710d869c2e77fc3f5539bcca13e38/xLuaDumper5.1/xlua.luac) and Lua Binary via Lua51 [here](https://github.com/formagGinoo/GuiLongchaoReverse/blob/df230e5044b710d869c2e77fc3f5539bcca13e38/xLuaDumper5.1/lua51.luac), so you can take a look yourself. The lua source code used can be found [here](https://github.com/formagGinoo/GuiLongchaoReverse/blob/df230e5044b710d869c2e77fc3f5539bcca13e38/xLuaDumper5.1/opcode.lua)

---

Feel free to contribute on this project [here](https://discord.com/channels/603359898507673630/1229379510324039780).
