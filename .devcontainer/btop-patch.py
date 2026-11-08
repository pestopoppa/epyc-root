from pathlib import Path

p = Path("/tmp/btop-1.3.2/src/linux/btop_collect.cpp")
text = p.read_text()
lines = text.splitlines(keepends=True)
changed = False
for i, line in enumerate(lines):
    if "rsmi_dev_power_ave_get" not in line:
        continue
    for j in range(i, min(i + 12, len(lines))):
        if 'else gpus_slice[i].gpu_percent.at("gpu-pwr-totals").push_back' in lines[j]:
            indent = lines[j][: len(lines[j]) - len(lines[j].lstrip())]
            lines[j] = lines[j].replace(
                '} else gpus_slice[i].gpu_percent.at("gpu-pwr-totals").push_back',
                "} else {\n"
                + indent
                + "    gpus_slice[i].pwr_usage = (long long)(power / 1000);\n"
                + indent
                + '    gpus_slice[i].gpu_percent.at("gpu-pwr-totals").push_back',
            )
            lines[j] = lines[j].rstrip() + " }\n"
            changed = True
            break
    if changed:
        break
if not changed:
    raise SystemExit("btop AMD pwr_usage target line not found")
p.write_text("".join(lines))
print("patched btop AMD pwr_usage")
