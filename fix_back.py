content = open('index.html').read()

# 버튼 텍스트를 더 잘 보이는 화살표로 변경하고 스타일 조정
old = '<button class="modal-back" onclick="closeModalBtn()">‹</button>'
new = '<button class="modal-back" onclick="closeModalBtn()">←</button>'
content = content.replace(old, new)

# font-size와 정렬 수정
old2 = '      font-size: 20px;\n      display: flex;\n      align-items: center;\n      justify-content: center;\n      font-weight: 200;'
new2 = '      font-size: 15px;\n      display: flex;\n      align-items: center;\n      justify-content: center;\n      font-weight: 600;\n      line-height: 1;'
content = content.replace(old2, new2)

open('index.html', 'w').write(content)
print('완료!')
