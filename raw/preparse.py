from lingpy import *
import re
from clldutils.text import strip_brackets
from collections import defaultdict
data = csv2list('data.tsv', strip_lines=False)
D = {0: ['doculect', 'concept', 'concept_in_source', 'chinese', 'value', 'form', 'cog']}
idx = 1
form2idx = {}
proto2idx = {}
concepts = defaultdict(list)
for i, row in enumerate(data[1:]):
    print(len(row))
    tmp = dict(zip(data[0], row))
    print(tmp)
    egl, cgl = tmp['Gloss'].split(';')
    gloss = ''
    cogid = row[0]
    for lng in ['PBz', 'TS', 'FX', 'XR', 'XL', 'CB', 'CJ']:
        words = [w.strip() for w in tmp[lng].replace('"', '').split(';')]
        if words:
            for word in words:
                if "'" in word:
                    gloss = re.findall("'([^']*?)'", word)[0]
                    form = word.split("'")[0]
                    form = strip_brackets(form)
                else:
                    form = strip_brackets(word)
                if form:
                    if lng == "PBz":
                        if egl in proto2idx:
                            D[proto2idx[egl]][-1] += [cogid]
                            D[proto2idx[egl]][4] += [word]
                            D[proto2idx[egl]][5] += [form]
                        else:
                            D[idx] = [lng, egl, gloss, cgl, [word], [form],
                                    [cogid]]
                            proto2idx[egl] = idx
                            idx += 1
                    else:

                        if (form, lng, egl) in form2idx:
                            D[form2idx[form, lng, egl]][-1] += [cogid]
                        else:
                            D[idx] = [lng, egl, gloss, cgl, word, form, [cogid]]
                            form2idx[form, lng, egl] = idx
                            idx += 1
                            concepts[egl, cgl] += [gloss]

for idx in D:
    if isinstance(D[idx][4], list):
        D[idx][4] = ' / '.join(D[idx][4])
        D[idx][5] = ' '.join(D[idx][5])
Wordlist(D).output('tsv', filename='wordlist', ignore='all', prettify=False)
with open('../etc/concepts.tsv', 'w') as f:
    f.write('\t'.join(['NUMBER', 'ENGLISH', 'CHINESE', 'GLOSSES_IN_SOURCE'])+'\n')
    for num, (egl, cgl) in enumerate(sorted(concepts, key=lambda x: x[0].lower())):
        f.write('\t'.join([str(num), egl, cgl, ' // '.join(list(
            set([x for x in concepts[num, egl, cgl] if x])))])+'\n')
                
        
