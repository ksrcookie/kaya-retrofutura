import shlex
def parse(line:str):
    t=shlex.split(line); 
    if not t: return None,{}
    cmd=t[0].lower(); pos=[]; kv={}
    for a in t[1:]:
        if '=' in a and not a.startswith('='): k,v=a.split('=',1); kv[k]=v
        else: pos.append(a)
    return cmd, {'pos':pos,'kv':kv,'raw':line}
