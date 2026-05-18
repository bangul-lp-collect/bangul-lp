content = open('index.html').read()
old = """    .modal-close {
      position: absolute;
      top: 16px;
      right: 16px;
      background: #333;
      border: none;
      color: #fff;
      width: 28px;
      height: 28px;
      border-radius: 50%;"""
new = """    .modal-back {
      position: absolute;
      top: 16px;
      left: 16px;
      background: rgba(255,255,255,0.15);
      backdrop-filter: blur(10px);
      border: none;
      color: #fff;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 200;
    }
    .modal-close {
      position: absolute;
      top: 16px;
      right: 16px;
      background: rgba(255,255,255,0.15);
      backdrop-filter: blur(10px);
      border: none;
      color: #fff;
      width: 28px;
      height: 28px;
      border-radius: 50%;"""
if old in content:
    open('index.html', 'w').write(content.replace(old, new))
    print('완료!')
else:
    print('못찾음')
