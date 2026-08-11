with open('app/main.py', encoding='utf-8') as f:
    lines = f.read().splitlines()
    for idx in range(230, min(275, len(lines))):
        print(idx+1, lines[idx])
