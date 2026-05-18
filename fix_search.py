content = open('index.html').read()
old = "const matchSearch = !q || [a.title, a.composer, a.performer, a.orchestra, a.label, a.conductor].some(v => v && v.toLowerCase().includes(q));"
new = "const terms = q.split(' ').filter(t => t.length > 0); const matchSearch = !q || terms.every(term => [a.title, a.composer, a.performer, a.orchestra, a.label, a.conductor].some(v => v && v.toLowerCase().includes(term)));"
if old in content:
    open('index.html', 'w').write(content.replace(old, new))
    print('완료!')
else:
    print('못찾음')
