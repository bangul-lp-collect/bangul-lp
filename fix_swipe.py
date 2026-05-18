content = open('index.html').read()

# 뒤로가기 버튼 제거
content = content.replace('<button class="modal-back" onclick="closeModalBtn()">←</button>', '')

# 스와이프 다운으로 모달 닫기 추가
old = 'function closeModal(e)'
new = '''// 스와이프로 모달 닫기
let touchStartY = 0;
document.getElementById('modalOverlay').addEventListener('touchstart', e => {
  touchStartY = e.touches[0].clientY;
});
document.getElementById('modalOverlay').addEventListener('touchend', e => {
  const diff = e.changedTouches[0].clientY - touchStartY;
  if (diff > 80) closeModalBtn();
});

function closeModal(e)'''
content = content.replace(old, new)

open('index.html', 'w').write(content)
print('완료!')
