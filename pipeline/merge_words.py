"""Junta tokens falados em um token de exibição para a legenda (ex.: 'oitenta e três dólares' -> 'US$ 83').
Uso: python3 merge_words.py   (lê words.json e merges.json no diretório atual; reescreve words.json)
merges.json: [[["oitenta","e","três","dólares"], "US$ 83,"], ...]  (tokens em minúsculas, sem pontuação)"""
import json, re
W = json.load(open('words.json')); merges = json.load(open('merges.json'))
def cl(w): return re.sub(r'[^\wÀ-ú-]', '', w).lower()
out = []; i = 0
while i < len(W):
    for seq, disp in merges:
        n = len(seq)
        if [cl(w['w']) for w in W[i:i+n]] == seq and all(w['p'] == W[i]['p'] for w in W[i:i+n]):
            out.append(dict(w=disp, p=W[i]['p'], s=W[i]['s'], e=W[i+n-1]['e'])); i += n; break
    else:
        out.append(W[i]); i += 1
json.dump(out, open('words.json', 'w'), ensure_ascii=False, indent=0)
print(len(W), '->', len(out))
