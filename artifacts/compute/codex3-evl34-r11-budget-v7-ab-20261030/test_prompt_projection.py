from prompt_projection import project
row={'question':'Where?','answer':'SECRET GOLD','context':{'title':['A','B'],'sentences':[['one.','two.'],['three.']]}}
expected='Answer the question using the documents. Give a concise answer.\n\n[A]\none. two.\n\n[B]\nthree.\n\nQuestion: Where?'
assert project(row)==expected and 'SECRET GOLD' not in project(row) and '\\n' not in project(row)
for bad in ({},row|{'context':{'title':['x'],'sentences':[]}}):
 try:project(bad)
 except ValueError:pass
 else:raise AssertionError('bad row accepted')
print('source projection exact newline bytes and gold exclusion passed')
