from lingpy import *
import re
from clldutils.text import strip_brackets
from collections import defaultdict
data = csv2list('data.tsv', strip_lines=False)
D = {0: ['doculect', 'concept', 'concept_in_source', 'chinese', 'value', 'form', 'cogid']}
idx = 1
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
                    D[idx] = [lng, egl, gloss, cgl, word, form, cogid]
                    idx += 1
                    concepts[cogid, egl, cgl] += [gloss]
Wordlist(D).output('tsv', filename='wordlist', ignore='all', prettify=False)
with open('../etc/concepts.tsv', 'w') as f:
    f.write('\t'.join(['NUMBER', 'ENGLISH', 'CHINESE', 'GLOSSES_IN_SOURCE'])+'\n')
    for num, egl, cgl in concepts:
        f.write('\t'.join([num, egl, cgl, ' // '.join(list(
            set([x for x in concepts[num, egl, cgl] if x])))])+'\n')
                
        
