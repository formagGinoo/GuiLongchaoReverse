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
