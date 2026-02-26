import struct
import platform
import sys

print(f"Bit: {struct.calcsize('P') * 8}")
print(f"Platform: {platform.platform()}")
print(f"Version: {sys.version}")
