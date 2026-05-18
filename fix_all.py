content = open('index.html').read()

# statusbar 완전 제거
import re
content = re.sub(r'\s*<div class="statusbar[^"]*">.*?</div>\s*', '\n', content, flags=re.DOTALL)
content = re.sub(r'\s*<div class="statusbar">.*?</div>\s*', '\n', content, flags=re.DOTALL)

# statusbar CSS 제거
content = re.sub(r'\s*\.statusbar[^{]*\{[^}]*\}', '', content)

open('index.html', 'w').write(content)
print('완료!')
