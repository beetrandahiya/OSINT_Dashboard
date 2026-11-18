import json, sys, io, contextlib
ARGS = sys.argv[1:]; sys.argv = ['x', 'c']
with contextlib.redirect_stdout(io.StringIO()):
    import gen_eye as G
NEW = json.load(open('newimg.json'))
mp = {v: f'../out_{k}.jpg' for k, v in G.IMG.items()}
mp.update({v: f'../out_{k}.jpg' for k, v in NEW.items()})
mp.update({'e21da2bc43f671b83667e82f41973a21': '../out_nearfull_grade.jpg', 'a648821de07caec2fc85cb87737d37d8': '../out_whole_grade.jpg', '40a16fae57632686edefd4f7dbe2a139': '../out_theatre_grade.jpg', '679870a0125ae2cafcfcab0051463c3a': '../out_theatre_noglow.jpg'})
for nm, _ in json.load(open(ARGS[0] if ARGS else 'denseboards.json')):
    s = open('../dc/project/' + nm).read()
    for k, v in mp.items(): s = s.replace('/_blob/' + k, v)
    open('prev/' + nm.replace('.dc.html', '.html'), 'w').write(s)
