with open('services/ai_local_service.py', 'r') as f:
    lines = f.readlines()

new_lines = []
in_class = False
for line in lines:
    if line.startswith('class AILocalService:'):
        in_class = True
        new_lines.append(line)
        continue
    if in_class:
        if line.startswith('        def '):
            new_lines.append('    ' + line.lstrip())
        elif line.strip() == '':
            new_lines.append('\n')
        elif line.startswith('        '):
            new_lines.append('        ' + line.lstrip())
        elif line.startswith('    '):
            new_lines.append('        ' + line.lstrip())
        else:
            # what if it's top-level or comment?
            if line.startswith('#'):
                new_lines.append('    ' + line)
            else:
                new_lines.append('        ' + line.lstrip())
    else:
        new_lines.append(line)

with open('services/ai_local_service.py', 'w') as f:
    f.writelines(new_lines)
