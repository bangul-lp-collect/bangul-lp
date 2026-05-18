content = open('index.html').read()

old = "  document.getElementById('modalOverlay').classList.add('show');"
new = "  document.getElementById('modalOverlay').classList.add('show');\n  document.body.style.overflow = 'hidden';"
content = content.replace(old, new)

old2 = "  document.getElementById('modalOverlay').classList.remove('show');"
new2 = "  document.getElementById('modalOverlay').classList.remove('show');\n  document.body.style.overflow = '';"
content = content.replace(old2, new2)

open('index.html', 'w').write(content)
print('완료!')
