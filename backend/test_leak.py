raw = "Halo Kak Vanny, berdasarkan laporan yang Anda berikan, sepertinya ada masalah dengan kedua layar POS Tiketing yang sering hidup mati. Hal ini mungkin disebabkan oleh koneksi kabel yang longgar atau driver error pada printer. Silakan periksa kembali kabel printer apakah sudah tersambung dengan benar dan coba restart PC kasir. Jika masalah masih berlanjut, silakan hubungi tim IT (PIC) untuk penanganan lebih lanjut. Root Cause: Koneksi kabel yang longgar atau driver error pada printer"

internal_keywords = [
    "Remember to follow ALL the rules",
    "Your job is on the line",
    "Thought:", "Action:", "Action Input:", "Observation:",
    "Final Answer:", "I need to", "I should", "I will",
    "Human:", "Assistant:", "System:", "> Entering", "> Finished",
]
for kw in internal_keywords:
    if kw.lower() in raw.lower():
        print("LEAK FOUND:", kw)

import re
has_chinese = bool(re.search(r'[\u4e00-\u9fff]', raw))
print("CHINESE:", has_chinese)
